"""
Proper structure for defining an app and its modules, to avoid
circular imports and allow the app context to be defined here,
and imported elsewhere in the app.

Adapted from:
https://suryasankar.medium.com/a-basic-app-factory-pattern-for-production-ready-websites-using-flask-and-sqlalchemy-dbb891cdf69f
https://stackoverflow.com/a/64680953
"""
import os
import json
import traceback
from flask import Flask, render_template
from flask_security import Security, login_required
from flask_mail import Mail
from flask_login import current_user
from flask_cors import CORS
from flask_security.forms import RegisterForm, Required
from wtforms import StringField
import flask_whooshalchemy as wa

import settings
from app.user import user_datastore, Role, User
from app.database import db
from app.reports.reports_server import rep
from app.geodata import postgis_db
from app.geodata.coord_converter import geo
from app.admin.admin_server import adm
from app.reports.reports_db import SpillReport

logger = settings.setup_logger(__name__)


def create_app(register_blueprints=True):
    app = Flask(__name__)

    # Basic settings for this app
    CORS(app)

    # Disable debug mode on prod
    if settings.PROD_SERVER:
        app.config["DEBUG"] = False

    app.config['UPLOAD_FOLDER'] = settings.attachments
    # Disable caching on downloaded files
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    app.config['UPLOAD_FOLDER'] = settings.attachments
    # Disable caching on downloaded files
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    # Related to user logins (Flask-security)
    app.config['DEBUG'] = True
    app.config['SECRET_KEY'] = settings.db_secret
    # postgresql://user:pass@localhost:5432/my_db
    app.config['SQLALCHEMY_DATABASE_URI'] = settings.SPILL_TRACKER_DB_URL
    app.config['SECURITY_REGISTERABLE'] = True
    # There is another configuration value to change the URL if desired:
    # Use cryptic URL to prevent spam registration
    app.config['SECURITY_REGISTER_URL'] = '/TuychXJzpBhv2mmZcGt8bQ'
    app.config['SECURITY_CHANGEABLE'] = True

    # We're using PBKDF2 with salt.
    app.config['SECURITY_PASSWORD_HASH'] = 'pbkdf2_sha512'
    app.config['SECURITY_PASSWORD_SALT'] = settings.db_salt
    # https://pythonhosted.org/Flask-Security/configuration.html#miscellaneous
    app.config['SECURITY_SEND_REGISTER_EMAIL'] = True

    # Disable caching on downloaded files
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    # SQLALCHEMY_TRACK_MODIFICATIONS must be *enabled* for flask-whooshalchemy3
    # fulltext search. If disabled, it will NOT propagate updates to the search index.
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    app.config['WHOOSH_INDEX_PATH'] = settings.WHOOSH_INDEX
    logger.info('WHOOSH_INDEX_PATH set to: %s' % settings.WHOOSH_INDEX)

    # Flask-Security optionally sends email notification to users upon registration, password reset, etc.
    # It uses Flask-Mail behind the scenes. Email-related config values are set here.
    app.config['SECURITY_RECOVERABLE'] = True
    app.config['SECURITY_EMAIL_SENDER'] = 'no-reply@marinepollution.ca'

    # SSL is disabled, use TLS instead to prevent this error:
    # ssl.SSLError: [SSL: WRONG_VERSION_NUMBER] wrong version number (_ssl.c:1123)
    # https://stackoverflow.com/a/66290550
    # app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USE_TLS'] = True

    # Use my own SMTP server settings here
    app.config['MAIL_SERVER'] = settings.smtp_server
    app.config['MAIL_PORT'] = settings.smtp_port
    app.config['MAIL_USERNAME'] = settings.smtp_user
    app.config['MAIL_PASSWORD'] = settings.smtp_pass

    # Load mailing lists from a file, if it exists
    # if os.path.exists(settings.MAILING_LIST_FILE):
    #     with open(settings.MAILING_LIST_FILE) as f:
    #         data = json.load(f)
    #
    #     # for key, value in data.items():
    #     #     app.config.update(
    #     #         key=value
    #     #     )
    #
    #     # app.config.update(
    #     #     **data
    #     # )
    #
    #     app.config.update(
    #         EMAIL_LISTS=data
    #     )

    # Initialize SQLAlchemy on this app
    db.init_app(app)

    # Use a custom registration form for new users
    # If we use a custom registration form, security confirmable MUST be turned off:
    # https://stackoverflow.com/a/56155594
    # https://github.com/mattupstate/flask-security/issues/54
    app.config['SECURITY_CONFIRMABLE'] = False

    class ExtendedRegisterForm(RegisterForm):
        staff_name = StringField('Full Name', [Required()])

    # Initialize Flask-Security in the app
    Security(app, user_datastore,
             register_form=ExtendedRegisterForm)

    # Initialize Flask-Mail in the app
    # We don't need the returned Mail object
    Mail(app)

    # All of the following must be done within an app context
    with app.app_context():
        # Create DB tables with the SQLAlchemyUserDatastore config as defined above
        logger.info('Initializing database...')
        db.create_all()

        # Executes before the first request is processed.
        @app.before_first_request
        def before_first_request():

            logger.info('Initializing user roles...')

            # Create the Roles, unless they already exist
            user_datastore.find_or_create_role(name='admin', description='Administrator')
            user_datastore.find_or_create_role(name='user', description='CCG User')
            user_datastore.find_or_create_role(name='observer', description='Observer with read-only access')

            postgis_db.create_map_view()

            # Create user tables in user_datastore
            db.session.commit()

            # Add core admin users: Load the admin role
            adm_role = Role.query.filter(Role.name == 'admin').first()

            # Add this role to each admin user
            for adm_email in settings.ADMIN_EMAILS:
                logger.info('Adding admin role for %s' % adm_email)
                try:
                    adm_user = User.query.filter(User.email == adm_email).first()
                    if not adm_user:
                        logger.warning('User does not exist: %s' % adm_email)
                        continue
                    adm_user.roles.append(adm_role)
                    db.session.add(adm_user)
                    db.session.commit()
                except:
                    logger.error('Cannot add admin role for: %s. Duplicate key violation?' % adm_email)
                    logger.error(traceback.format_exc())

        # Always add current user and admin flag to templates
        # https://stackoverflow.com/a/26498865
        @app.context_processor
        def inject_user():
            return dict(user=current_user)

        @rep.context_processor
        def inject_admin_flag():
            return dict(is_admin=current_user.has_role('admin'))

        # Register blueprints for Reports and other endpoints, only after creating user tables
        app.register_blueprint(rep)
        app.register_blueprint(geo)
        app.register_blueprint(adm)

        # Add search index for reports
        logger.info('Adding whoosh fulltext index for SpillReport...')
        wa.search_index(app, SpillReport)

        # from app.user import User
        # wa.search_index(app, User)
        # wa.create_index(app, User)

        # @app.route('/su/<query_text>', methods=['GET'])
        # def user_search(query_text):
        #     # session = db.Session()
        #     # q = session.query(SpillReport)
        #     # results = q.search(query_text).all()
        #     # results = db.SpillReport.query.search(q, limit=10)
        #     results = User.query.search(query_text)
        #     print(results)

        # Add index endpoint
        @app.route('/', methods=['GET'])
        @login_required
        def index():
            # Users must be authenticated to view the home page, but they don't have to have any particular role.
            # Flask-Security will display a login form if the user isn't already authenticated.
            logger.info('Homepage requested by: %s (id %s)' % (current_user.email, current_user.id))
            return render_template('index.html',
                                   is_admin=current_user.has_role('admin'))
                                   # user=current_user)

        # Auth endpoint for nginx: https://stackoverflow.com/a/55737013
        # Allow redirect to Geoserver if auth OK
        @app.route("/auth", methods=['GET', 'POST'])
        def nginx_auth():
            if current_user.is_authenticated:
                logger.info('Auth request OK')
                return 'You are logged in!'
            else:
                msg = 'Sorry, but unfortunately you are not logged in.'
                logger.warning('Auth request failed: %s' % msg)
                return msg, 401

        return app
