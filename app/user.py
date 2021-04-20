
from app.database import db
from flask_security import (
    SQLAlchemyUserDatastore, UserMixin, RoleMixin)

import settings
logger = settings.setup_logger(__name__)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    staff_name = db.Column(db.String(255))
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=False)
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary='user_roles',
                            backref=db.backref('users', lazy='dynamic'))


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


def list_all_users():
    """
    Get a list of all users and their role (each user should have only one role)
    :return:
    """
    users = User.query.all()
    display_users = []
    for u in users:
        disp_user = {'id': u.id,
            'staff_name': u.staff_name,
            'email': u.email}
        logger.info(u.staff_name)
        # Check if user is no longer active
        if not u.active:
            logger.warning('User %s is not active' % u.staff_name)
            disp_user['role'] = 'nologin'
        else:
            # Check if user has roles
            if not u.roles:
                # Default observer if not defined
                disp_user['role'] = 'observer'
            else:
                # Get the first role (should be the only)
                disp_user['role'] = u.roles[0].name
        display_users.append(disp_user)

    return display_users


def set_user_access(user_id, role_name):

    # Get user by id
    u = User.query.filter(User.id == user_id).first()
    save = False

    if role_name == 'nologin':
        # Set user to inactive
        u.active = False
        save = True
        # db.session.add(u)
        # db.session.commit()
    else:
        # Ensure that user is active (this allows reactivating users who
        # were previously deactivated)
        if not u.active:
            logger.info('Activating user: %s' % u.staff_name)
            u.active = True
            save = True
        # Check if role needs to be updated. Get list of existing roles
        current_roles = [role.name for role in u.roles]
        if role_name not in current_roles:
            # Use the role name as-is. Get matching role from db
            role = Role.query.filter(Role.name == role_name).first()
            # Clear existing roles
            u.roles.clear()
            u.roles.append(role)
            logger.info('Updated user %s with role: %s' % (
                u.staff_name, role_name))
            save = True

    # Save user data if needed
    if save:
        db.session.add(u)
        db.session.commit()
