import os
import sys
from datetime import datetime
import logging
import socket
from dotenv import load_dotenv
load_dotenv()


def dev_machine():
    return socket.gethostname() == 'chas-2.local'


# Logging setup
def safe_timestamp():
    now = datetime.now()
    return now.strftime(filesafe_timestamp)


def display_timestamp():
    now = datetime.now()
    return now.strftime(display_date_fmt)


# Logging format
screen_fmt = logging.Formatter(
    '%(asctime)s:%(levelname)s:%(module)s(%(lineno)d) - %(message)s'
)


def setup_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    sh = logging.StreamHandler()
    sh.setFormatter(screen_fmt)
    sh.setLevel(level)
    logger.addHandler(sh)
    return logger


logger = setup_logger(__name__)

base_dir = os.path.dirname(os.path.realpath(__file__))

display_date_fmt = '%Y-%m-%d %H:%M:%S'
filesafe_timestamp = '%Y%m%d-%H%M%S'
html_timestamp = '%Y-%m-%dT%H:%M'
ccg_display_fmt = '%Y-%m-%d %H%M'

IMAGE_FORMATS = ['jpg', 'jpeg', 'tif', 'tiff', 'png']
ALLOWED_EXTENSIONS = IMAGE_FORMATS + ['doc', 'docx', 'pdf']

PROD_SERVER = socket.gethostname() == 'spilltracker'


# Db conn settings
SPILL_TRACKER_DB_URL = os.environ.get('SPILL_TRACKER_DB_URL')
if not SPILL_TRACKER_DB_URL:
    print('CRITICAL: SPILL_TRACKER_DB_URL env var is required')
    sys.exit(1)

# Generated with secrets.token_urlsafe(16)
db_secret = os.environ.get('SPILLDB_SECRET')
db_salt = os.environ.get('SPILLDB_SALT')
# db_user = os.environ.get('PGUSER')
# db_name = os.environ.get('PGDATABASE')
# db_pass = os.environ.get('PGPASSWORD')
# db_host = os.environ.get('PGHOST')
# db_port = os.environ.get('PGPORT')
if not db_secret or not db_salt:
    logger.error('SPILLDB_SECRET and SPILLDB_SALT env vars required!')
    sys.exit(1)

# Load Email credentials
smtp_user = os.environ.get('SPILL_SMTP_USER')
smtp_pass = os.environ.get('SPILL_SMTP_PASS')
smtp_server = 'email-smtp.ca-central-1.amazonaws.com'
smtp_port = 587
# print('%s %s' % (smtp_user, smtp_pass))
