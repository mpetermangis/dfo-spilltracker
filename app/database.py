from flask_sqlalchemy import SQLAlchemy

# define global extensions in a separate file so that they can be imported from
# anywhere else in the code without creating circular imports
# the proper initialization is made within the `create_app` function
db = SQLAlchemy()
