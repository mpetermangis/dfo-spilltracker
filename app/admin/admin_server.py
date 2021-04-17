"""
This is the Flask endpoint for admin tasks. All URLs in this server
require the Admin role.
"""

from flask import Blueprint, request, jsonify
from flask_security import roles_required

# Flask blueprint for admin page
adm = Blueprint('admin', __name__, url_prefix='/admin')

# @route() must always be the outer-most decorator
# https://flask-user.readthedocs.io/en/latest/authorization.html
@adm.route('/')
@roles_required('admin')
def admin():
    return 'Hello admin'
