import os
import sys
from datetime import datetime
import logging
import socket


base_dir = os.path.dirname(os.path.realpath(__file__))

display_date_fmt = '%Y-%m-%d %H:%M:%S'
filesafe_timestamp = '%Y%m%d-%H%M%S'
html_timestamp = '%Y-%m-%dT%H:%M'

IMAGE_FORMATS = ['jpg', 'jpeg', 'tif', 'tiff', 'png']
ALLOWED_EXTENSIONS = IMAGE_FORMATS + ['doc', 'docx', 'pdf']


# Db conn settings
SPILL_TRACKER_DB_URL = os.environ.get('SPILL_TRACKER_DB_URL')
if not SPILL_TRACKER_DB_URL:
    print('CRITICAL: SPILL_TRACKER_DB_URL env var is required')
    sys.exit(1)


def dev_machine():
    return socket.gethostname() == 'chas-2.local'


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
