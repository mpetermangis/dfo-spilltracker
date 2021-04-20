"""
This is the Flask endpoint for admin tasks. All URLs in this server
require the Admin role.
"""
import json
import settings
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_security import roles_required
from flask_login import current_user
from app import user

logger = settings.setup_logger(__name__)

# Get a reference to the app to work with here.
# from app.app_factory import create_app
# logger.info('Creating app object in %s' % __name__)
# app = create_app()

# Flask blueprint for admin page
adm = Blueprint('admin', __name__, url_prefix='/admin')


# @route() must always be the outer-most decorator
# https://flask-user.readthedocs.io/en/latest/authorization.html
@adm.route('/')
@roles_required('admin')
def admin_page():

    logger.info('Admin page requested')

    # Get all users with roles
    users = user.list_all_users()
    # TODO: dont store this in a JSON file! Use a proper DB table.
    mailing_lists = load_mailing_list()
    return render_template('admin_page.html',
                           users=users,
                           mailing_lists=mailing_lists)


@adm.route('/save_adm', methods=['POST'])
@roles_required('admin')
def save_admin_data():
    data = request.form
    if data:
        data = data.to_dict()

        # Read user data, email list
        for key, value in data.items():
            if key.startswith('userid-'):
                user_id = key.replace('userid-', '')
                try:
                    user_id = int(user_id)
                except:
                    logger.error('Invalid user ID: %s' % user_id)
                    continue

                user.set_user_access(user_id, value)

            # Get email lists
            elif key.startswith('MAIL_LIST'):
                # Save the new mailing list
                logger.info('Save mailing list: %s' % key)
                save_mailing_list(key, value)

        logger.info('Saved Admin data OK, redirect to admin page')
        return redirect(url_for('admin.admin_page'))

    else:
        status = 'No data submitted'
        resp = jsonify(success=False, msg=status)
        return resp


def load_mailing_list():
    with open(settings.MAILING_LIST_FILE) as f:
        data = json.load(f)
    return data.get('lists')


def save_mailing_list(list_name, emails):
    mail_lists = load_mailing_list()

    # List of mailing lists
    mail_lists_updated = []

    for ml in mail_lists:

        if ml.get('name') == list_name:
            ml['emails'] = emails
        mail_lists_updated.append(ml)

    # # Set mailing list emails
    # mail_list = data.get(list_name)
    # if not mail_list:
    #     logger.error('Mailing list %s not found!' % list_name)
    #     return
    # data[list_name]['emails'] = emails
    data = {'lists': mail_lists_updated}

    with open(settings.MAILING_LIST_FILE, 'w') as f:
        json.dump(data, f, indent=2)
