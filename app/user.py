from app.database import db
from flask_security import (
    SQLAlchemyUserDatastore, UserMixin, RoleMixin)

# Define user models
# roles_users = db.Table('roles_users',
#                            db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
#                            db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    staff_name = db.Column(db.String(255))
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=False)
    confirmed_at = db.Column(db.DateTime())
    # roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    roles = db.relationship('Role', secondary='user_roles', backref=db.backref('users', lazy='dynamic'))


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


# Define the UserRoles association table
class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('role.id', ondelete='CASCADE'))



user_datastore = SQLAlchemyUserDatastore(db, User, Role)

