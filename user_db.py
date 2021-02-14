
import settings
import os
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required
from flask import current_app as app

user_tables = SQLAlchemy(app)

# Define models
roles_users = user_tables.Table('roles_users',
                                user_tables.Column('user_id', user_tables.Integer(), user_tables.ForeignKey('user.id')),
                                user_tables.Column('role_id', user_tables.Integer(), user_tables.ForeignKey('role.id')))


class Role(user_tables.Model, RoleMixin):
    id = user_tables.Column(user_tables.Integer(), primary_key=True)
    name = user_tables.Column(user_tables.String(80), unique=True)
    description = user_tables.Column(user_tables.String(255))


class User(user_tables.Model, UserMixin):
    id = user_tables.Column(user_tables.Integer, primary_key=True)
    email = user_tables.Column(user_tables.String(255), unique=True)
    staff_name = user_tables.Column(user_tables.String(255))
    password = user_tables.Column(user_tables.String(255))
    active = user_tables.Column(user_tables.Boolean, default=False)
    confirmed_at = user_tables.Column(user_tables.DateTime())
    roles = user_tables.relationship('Role', secondary=roles_users,
                                     backref=user_tables.backref('users', lazy='dynamic'))


def get_username(id):
    session = user_tables.Session()


# Initialize the SQLAlchemy data store and Flask-Security.
user_datastore = SQLAlchemyUserDatastore(user_tables, User, Role)


def create_user_db():
    # Create any user/role database tables that don't exist yet.
    user_tables.create_all()

    # Create the Roles, unless they already exist
    user_datastore.find_or_create_role(name='admin', description='Administrator')
    user_datastore.find_or_create_role(name='user', description='CCG User')
    user_datastore.find_or_create_role(name='observer', description='Observer with read-only access')

    user_tables.session.commit()
