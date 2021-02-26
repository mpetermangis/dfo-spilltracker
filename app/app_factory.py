"""
Proper structure for defining an app and its modules, to avoid
circular imports and allow the app context to be defined here,
and imported elsewhere in the app.

Adapted from:
https://suryasankar.medium.com/a-basic-app-factory-pattern-for-production-ready-websites-using-flask-and-sqlalchemy-dbb891cdf69f
https://stackoverflow.com/a/64680953
"""

from flask import Flask, render_template
from flask_security import Security, login_required
from flask_login import current_user
from flask_cors import CORS
from flask_security.forms import RegisterForm, Required
from wtforms import StringField

from app import settings
from app.user import user_datastore
from app.database import db
from app.reports.reports_server import rep
from app.geodata.coord_converter import geo
from app.admin.admin_server import adm

logger = settings.setup_logger(__name__)


def create_app(register_blueprints=True):
    app = Flask(__name__)

    # Basic settings for this app
    CORS(app)

    # Disable debug mode on prod
    # if socket.gethostname() == 'spilltracker':
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
    # Disable track modifications: https://github.com/pallets/flask-sqlalchemy/issues/365
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Flask-Security optionally sends email notification to users upon registration, password reset, etc.
    # It uses Flask-Mail behind the scenes.
    # Set mail-related config values.
    app.config['SECURITY_RECOVERABLE'] = True
    app.config['SECURITY_EMAIL_SENDER'] = 'no-reply@marinepollution.ca'

    # SSL disabled, use TLS instead to prevent this error:
    # ssl.SSLError: [SSL: WRONG_VERSION_NUMBER] wrong version number (_ssl.c:1123)
    # https://stackoverflow.com/a/66290550
    # app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USE_TLS'] = True

    # Use my own SMTP server settings here
    app.config['MAIL_SERVER'] = settings.smtp_server
    app.config['MAIL_PORT'] = settings.smtp_port
    app.config['MAIL_USERNAME'] = settings.smtp_user
    app.config['MAIL_PASSWORD'] = settings.smtp_pass

    # Initialize SQLAlchemy on this app
    db.init_app(app)

    # Use a custom registration form for new users
    # If we use a custom registration form, security confirmable MUST be turned off:
    # https://stackoverflow.com/a/56155594
    # https://github.com/mattupstate/flask-security/issues/54
    app.config['SECURITY_CONFIRMABLE'] = False

    class ExtendedRegisterForm(RegisterForm):
        staff_name = StringField('Full Name', [Required()])

    # Apply Flask-Security to the app
    Security(app, user_datastore,
             register_form=ExtendedRegisterForm)

    # All of the following must be done within an app context
    with app.app_context():
        # Create DB tables with the SQLAlchemyUserDatastore config as defined above
        db.create_all()

        # Executes before the first request is processed.
        @app.before_first_request
        def before_first_request():
            # Create any user/role database tables that don't exist yet.
            # No, this is done in user_db
            # pass
            # user_tables.userdb.create_all()
            # userdb.create_all()

            # Create the Roles, unless they already exist
            user_datastore.find_or_create_role(name='admin', description='Administrator')
            user_datastore.find_or_create_role(name='user', description='CCG User')
            user_datastore.find_or_create_role(name='observer', description='Observer with read-only access')

            # user_tables.userdb.session.commit()
            db.session.commit()

        # Always add current user to templates
        @app.context_processor
        def inject_user():
            return dict(user=current_user)

        # Register blueprints for Reports and other endpoints, only after creating user tables
        app.register_blueprint(rep)
        app.register_blueprint(geo)
        app.register_blueprint(adm)

        # Add index endpoint
        @app.route('/', methods=['GET'])
        @login_required
        def index():
            # Users must be authenticated to view the home page, but they don't have to have any particular role.
            # Flask-Security will display a login form if the user isn't already authenticated.
            # user = get_current_user()
            logger.info('Homepage loaded by: %s (id %s)' % (current_user.email, current_user.id))
            return render_template('index.html',
                                   user=current_user)

        return app
