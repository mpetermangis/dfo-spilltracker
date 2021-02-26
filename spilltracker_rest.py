# TODO: better structure for the app https://stackoverflow.com/a/64680953

from flask import Flask, flash, request, jsonify, send_file, render_template, redirect, url_for, session
from flask_login import current_user
from flask_security.forms import RegisterForm, Required
from wtforms import StringField
# BooleanField, Field, HiddenField, PasswordField, \
#     , SubmitField, ValidationError, validators
from flask_cors import CORS
from flask_mail import Mail
# from werkzeug.utils import secure_filename
import atexit
import settings
# import lookups
# import reports_db as db
import os
import socket
from geo import coord_converter
# import user_db
# user_db.create_user_db()


# Flask login / security modules
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required

logger = settings.setup_logger(__name__)
port = 5000

# app = Flask(__name__, static_folder="attachments")
app = Flask(__name__)
CORS(app)


# Disable debug mode on prod
# if socket.gethostname() == 'spilltracker':
if settings.PROD_SERVER:
    app.config["DEBUG"] = False

app.config['UPLOAD_FOLDER'] = settings.attachments
# Disable caching on downloaded files
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0


# Good example of Flask initialization
# https://gist.github.com/skyuplam/ffb1b5f12d7ad787f6e4

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


# Add SQLAlchemy and Flask-Mail to the Flask app
mail = Mail(app)
userdb = SQLAlchemy(app)

# Define models
roles_users = userdb.Table('roles_users',
                           userdb.Column('user_id', userdb.Integer(), userdb.ForeignKey('user.id')),
                           userdb.Column('role_id', userdb.Integer(), userdb.ForeignKey('role.id')))


class Role(userdb.Model, RoleMixin):
    id = userdb.Column(userdb.Integer(), primary_key=True)
    name = userdb.Column(userdb.String(80), unique=True)
    description = userdb.Column(userdb.String(255))


class User(userdb.Model, UserMixin):
    id = userdb.Column(userdb.Integer, primary_key=True)
    email = userdb.Column(userdb.String(255), unique=True)
    staff_name = userdb.Column(userdb.String(255))
    password = userdb.Column(userdb.String(255))
    active = userdb.Column(userdb.Boolean, default=False)
    confirmed_at = userdb.Column(userdb.DateTime())
    roles = userdb.relationship('Role', secondary=roles_users,
                                backref=userdb.backref('users', lazy='dynamic'))


# Use a custom registration form for new users
# If we use a custom registration form, security confirmable MUST be turned off:
# https://stackoverflow.com/a/56155594
# https://github.com/mattupstate/flask-security/issues/54
app.config['SECURITY_CONFIRMABLE'] = False
class ExtendedRegisterForm(RegisterForm):
    staff_name = StringField('Full Name', [Required()])

# Initialize SQLAlchemy and Flask-Security datastore.
user_datastore = SQLAlchemyUserDatastore(userdb, User, Role)
security = Security(app, user_datastore,
         register_form=ExtendedRegisterForm)

# Create DB tables with the SQLAlchemyUserDatastore config as defined above
userdb.create_all()


# Executes before the first request is processed.
@app.before_first_request
def before_first_request():
    # Create any user/role database tables that don't exist yet.
    # No, this is done in user_db
    # pass
    # user_tables.userdb.create_all()
    userdb.create_all()

    # Create the Roles, unless they already exist
    user_datastore.find_or_create_role(name='admin', description='Administrator')
    user_datastore.find_or_create_role(name='user', description='CCG User')
    user_datastore.find_or_create_role(name='observer', description='Observer with read-only access')

    # user_tables.userdb.session.commit()
    userdb.session.commit()


# Always add current user to templates
@app.context_processor
def inject_user():
    return dict(user=current_user)


# Register blueprints for Reports endpoint, only after creating user tables
from reports_server import rep
import excel_export
app.register_blueprint(rep)


@app.route('/bb', methods=['GET'])
def bb():
    return render_template('security/base.html')


@app.route('/', methods=['GET'])
@login_required
def index():
    # Users must be authenticated to view the home page, but they don't have to have any particular role.
    # Flask-Security will display a login form if the user isn't already authenticated.
    # user = get_current_user()
    logger.info('Homepage loaded by: %s (id %s)' % (current_user.email, current_user.id))
    return render_template('index.html',
                           user=current_user)


@app.route('/latlon_to_coords', methods=['POST'])
def latlon_to_coords():
    data = request.json
    coords = coord_converter.convert_from_latlon(
        data.get('lat'), data.get('lng'))
    return jsonify(success=True, data=coords), 200


@app.route('/chk_coordinates', methods=['POST'])
def chk_coordinates():
    data = request.json
    coordinate_type = data.get('coordinate_type')
    coord_str = data.get('coord_str')
    status, latitude, longitude = coord_converter.convert_to_latlon(
        coordinate_type, coord_str)
    if not status == 'OK':
        return jsonify(success=False, msg=status), 400
    else:
        data = {'lat': latitude, 'lon': longitude}
        return jsonify(success=True, msg=status, data=data), 200


@app.route('/all_data', methods=['GET'])
def db_dump():
    # Divide db dump by project
    export_file = excel_export.dump_all_excel()
    return send_file(export_file,
                     as_attachment=True,
                     attachment_filename=os.path.basename(export_file))


def stop_app():
    logger.info('Shutting down server:  Closing databases...')
    # projdb.close_db()


def main():
    # THIS MAIN METHOD IS ***NOT*** CALLED IF RUNNING FROM WSGI!
    # If running under WSGI, do logging config etc in the WSGI module, not here.
    # ONLY FOR LOCAL DEVELOPMENT

    start_msg = 'Spilltracker DEVELOPMENT Flask server on port %s' % port
    logger.info(start_msg)

    atexit.register(stop_app)

    app.run(
        # host="0.0.0.0",
        host="localhost",
        port=port,
        ssl_context='adhoc',
        debug=True
    )


if __name__ == '__main__':
    main()


