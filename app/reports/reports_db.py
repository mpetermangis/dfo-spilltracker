
import os
import re
from datetime import datetime, timedelta, date
from sqlalchemy import create_engine, Column, Integer, Text, DateTime, Float
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError
from sqlalchemy.schema import Sequence, CreateSequence
import traceback

import settings
from app.utils import lookups, notifications
from app.geodata import coord_converter, postgis_db
from app.user import User
from app.database import db
from whoosh.analysis import StemmingAnalyzer

engine = create_engine(settings.SPILL_TRACKER_DB_URL)

logger = settings.setup_logger(__name__)


"""
Create a view with latest version of each report, with coordinates converted to a 
PostGIS point object. Something like:

SELECT DISTINCT ON (report_num) * FROM public.spill_reports 
WHERE latitude IS NOT NULL AND longitude IS NOT NULL
ORDER BY report_num, last_updated DESC;

"""


# Define database schema
class SpillReport(db.Model):

    __tablename__ = "spill_reports"
    __searchable__ = ['report_num', 'report_name', 'update_text', 'name_reporter',
                      'phone_reporter', 'email_reporter', 'location_description',
                      'pollutant', 'pollutant_details', 'quantity', 'quantity_units',
                      'colour_odour', 'origin', 'weather', 'situation_info',
                      'vessel_name', 'call_sign', 'vessel_type', 'owner_agent',
                      'vessel_additional_info', 'er_region']

    __analyzer__ = StemmingAnalyzer()

    # Internal fields, not necessarily part of Spill Report schema
    id = Column(Integer,
                primary_key=True,
                nullable=False)
    last_updated = Column(DateTime,
                          nullable=False)
    recorded_by = Column(Text)
    user_id = Column(Integer, nullable=False)
    """
    ForeignKey doesn't work:
    sqlalchemy.exc.NoReferencedTableError: Foreign key associated with column 'spill_reports.user_id' 
    could not find table 'user' with which to generate a foreign key to target column 'id'
    user_id = Column(Integer, ForeignKey("user.id"),
                     nullable=False)
    """

    # report_num CANNOT be unique, since we have multiple versions of
    # the same report number with different timestamps.
    # This means it cannot used as a foreign key.
    report_num = Column(Text, nullable=False)
    report_name = Column(Text)
    update_text = Column(Text)
    report_date = Column(DateTime)
    report_timezone = Column(Text)
    spill_date = Column(DateTime)
    spill_timezone = Column(Text)
    name_reporter = Column(Text)
    phone_reporter = Column(Text)
    email_reporter = Column(Text)

    # Situation details
    coordinate_type = Column(Text)
    # coordinate_type = Column(Enum(CoordType))
    coordinates = Column(Text)
    # Calculated lat-long coords stored internally
    latitude = Column(Float)
    longitude = Column(Float)
    # Coordinates blank should be calculated automatically, not a stored field
    location_description = Column(Text)
    pollutant = Column(Text)
    pollutant_details = Column(Text)
    quantity = Column(Text)
    quantity_units = Column(Text)
    colour_odour = Column(Text)
    origin = Column(Text)
    weather = Column(Text)
    situation_info = Column(Text)
    # Pictures/Attachments: are in a separate table
    response_activated = Column(Text)

    # Vessel information
    vessel_name = Column(Text)
    call_sign = Column(Text)
    vessel_length = Column(Text)
    vessel_type = Column(Text)
    owner_agent = Column(Text)
    vessel_additional_info = Column(Text)

    # Alert List
    ccg_duty_officer = Column(Text)
    tc_marine_safety = Column(Text)
    vancouver_hm = Column(Text)
    area_mcts_centre = Column(Text)
    dfo_public_affairs = Column(Text)
    roc_officer = Column(Text)

    # Additional fields added Feb 2021
    # Done: add these fields to report form, and report display
    er_region = Column(Text)
    fleet_tasking = Column(Text)
    station_or_ship = Column(Text)
    unit = Column(Text)
    severity = Column(Integer)

    def __repr__(self):
        # This is how our object is printed
        return '%s (%s)' % (self.report_name, self.report_num)


class AttachedFile(db.Model):

    __tablename__ = "attachments"

    id = Column(Integer,
                primary_key=True,
                nullable=False)
    # Cannot use report_num as a foreign key because not unique.
    # report_num = Column(Text, ForeignKey('spill_reports.report_num'))
    report_num = Column(Text, nullable=False)
    # spill_id = Column(Integer, ForeignKey('spill_reports.spill_id'))
    # spill_id = Column(Integer, nullable=False)
    filename = Column(Text, nullable=False)
    type = Column(Text, nullable=False)

# Create a polrep sequence to generate unique POLREP numbers
logger.info('Creating DB sequence polrep_num')
polrep_seq = Sequence('polrep_num')
try:
    engine.execute(CreateSequence(polrep_seq))
    logger.info('Sequence created OK')
except ProgrammingError:
    # Sequence already exists, ignore
    logger.warning('Sequence "polrep_num" exists.')
    pass


# TODO; Update sequence on Jan 1
# Use the ALTER SEQUENCE command to modify PostgreSQL sequences.
# There is no built-in SQLAlchemy function for this, use session.execute to execute the SQL.
# https://stackoverflow.com/a/36248764
# db.session.execute("ALTER SEQUENCE test_id_seq RESTART WITH 1")
# db.session.commit()


def get_next_polrep_num():
    """
    Get the next polrep num in the DB sequence.
    :return:
    """
    next_polrep_num = engine.execute(polrep_seq)
    year = date.today().year
    next_polrep_num = '%s-%s' % (year, next_polrep_num)
    logger.info('Next POLREP number: %s' % next_polrep_num)
    return next_polrep_num


def result_to_dict(res):
    res_dict = {x.name: getattr(res, x.name) for x in res.__table__.columns}
    return res_dict


def null_to_empty_string(data):
    # Convert None in data (from db) to empty string for display
    display_data = {}
    for key, value in data.items():
        if value is None:
            value = ''
        display_data[key] = value
    return display_data


def empty_string_to_null(data):
    # Convert empty string for display to None for DB
    db_data = {}
    for key, value in data.items():
        db_data[key] = value
        if type(value) is str:
            if len(value.strip()) == 0:
                db_data[key] = None
    return db_data


def format_timestamps(data):
    report_date = data.get('report_date')
    spill_date = data.get('spill_date')
    report_timezone = data.get('report_timezone')
    spill_timezone = data.get('spill_timezone')
    last_updated = data.get('last_updated')
    data['last_updated_ts'] = last_updated.strftime(settings.filesafe_timestamp)
    data['last_updated_ccg'] = last_updated.strftime(settings.ccg_display_fmt)
    if report_date:
        data['report_date_html'] = report_date.strftime(settings.html_timestamp)
        data['report_date_ccg'] = report_date.strftime(settings.ccg_display_fmt)
        data['report_tz_ccg'] = lookups.tz_reversed.get(report_timezone)
    if spill_date:
        data['spill_date_html'] = spill_date.strftime(settings.html_timestamp)
        data['spill_date_ccg'] = spill_date.strftime(settings.ccg_display_fmt)
        data['spill_tz_ccg'] = lookups.tz_reversed.get(spill_timezone)
    return data


def list_all_reports():
    """
    Retrieve a summary of all reports.
    Get all fields here and render only the ones we want to display in the *template*
    Get only the latest version of each report.
    Order by last_updated, desc
    :return:
    """
    logger.info('Querying all reports...')
    results = SpillReport.query.all()
    reports_all = {}
    logger.info('Preparing %s reports for display' % len(results))
    for res in results:
        report = result_to_dict(res)
        # Convert None to empty string
        report = null_to_empty_string(report)
        # Check if this report_num is already in dict
        report_num = report.get('report_num')
        if report_num not in reports_all:
            reports_all[report_num] = report
        else:
            # Retrieve existing, compare last updated date, keep newest
            temp_report = reports_all.get(report_num)
            if report.get('last_updated') > temp_report.get('last_updated'):
                # This version is newer, replace
                reports_all[report_num] = report
    reports_list = list(reports_all.values())
    reports_list = sorted(reports_list, key=lambda i: i['last_updated'], reverse=True)
    logger.info('Report list is ready')
    return reports_list


def reports_by_date(results, reverse=False):
    """
    Transform SQLalchemy results to an ordered list of dicts, ordered by date
    :param results:
    :return:
    """
    report_data = []
    for r in results:
        res_dict = result_to_dict(r)
        report_data.append(res_dict)

    # Sort by last updated, reversed if needed
    report_data = sorted(report_data, key=lambda i: i['last_updated'], reverse=reverse)
    return report_data


def get_report(report_num, ts_url=None):
    """
    Retrieve a spill report at a given timestamp
    :param report_num:
    :param ts_url: a timestamp in URL-safe format
    :return: spill report as a Python dict
    """

    if not ts_url:
        # Get the latest (2 most recent versions) of this report
        results = SpillReport.query.filter(
            SpillReport.report_num==report_num).order_by(
                SpillReport.last_updated.desc()
            ).limit(2).all()

    else:
        # Get update at a specific timestamp
        # Convert ts_url to a timestamp object
        timestamp = datetime.strptime(ts_url, settings.filesafe_timestamp)
        results = SpillReport.query.filter(
            SpillReport.report_num == report_num,
            SpillReport.last_updated <= timestamp).order_by(
                SpillReport.last_updated.desc()
            ).limit(2).all()

    """
    Most efficient setup is:
    - the latest timestamp for each report_num should contain the complete representation 
    of the latest spill report. This means that retrieval of any latest spill report is O(1). 
    - in fact, getting any version of any report will be O(1)
    - Whenever a spill report is updated, we simply add a new record with all of the form data 
    (including older versions of some fields that are duplicated, that's fine), and mark it as the 
    latest.  Or do we even need to do that, can we use SQLalchemy to get a last() from a filter?
    - getting the latest version of ALL reports then becomes O(n).  Can probably do it one query, 
    filter the results in regular python, outside of SQLalchemy. 
    """

    if not results:
        logger.warning('Report num %s does not exist!' % report_num)
        return None

    final_report = result_to_dict(results[0])
    if len(results) < 2:
        logger.warning('No previous report for %s' % report_num)
        last_report = {}
    else:
        last_report = result_to_dict(results[1])

    return final_report, last_report


def format_coordinates(report):
    """
    Set values of coordinates and placeholders for HTML form
    :param report:
    :return:
    """
    # Add coordinate regex and placeholder, use default of Decimal Degrees
    coord_type = report.get('coordinate_type')
    if not coord_type:
        coord_type = 'Decimal Degrees'
    coord_pattern = ''
    coord_placeholder = ''
    coord_help = 'Format: '
    if coord_type == 'Decimal Degrees':
        coord_pattern = '\d{1,2}\.\d+,-\d{1,3}\.\d+'
        coord_placeholder = 'XX.XXX,-XXX.XXX'
    elif coord_type == 'Degrees Decimal Minutes':
        coord_pattern = '\d{2} \d{1,2}\.\d+ [Nn] \d{2,3} \d{1,2}\.\d+ [Ww]'
        coord_placeholder = 'XX XX.XXX N XXX XX.XXX W'
    elif coord_type == 'Degrees Minutes Seconds':
        coord_pattern = '\d{2} \d{1,2} \d{1,2} [Nn] \d{2,3} \d{1,2} \d{1,2} [Ww]'
        coord_placeholder = 'XX XX XX N XXX XX XX W'

    report['coord_pattern'] = coord_pattern
    report['coord_placeholder'] = coord_placeholder
    report['coord_help'] = coord_help + coord_placeholder
    report['coordinate_type'] = coord_type
    return report


def set_user_name(report):
    """
    Get user name from DB and set fields for display
    :param report:
    :return:
    """
    # Get user's full name from user_id
    user = User.query.filter(User.id == report.get('user_id')).first()
    if user:
        report['recorded_by'] = user.staff_name
    else:
        # Try to get name from recorded_by field (e.g. legacy reports)
        recorded_by = report.get('recorded_by')
        if recorded_by:
            report['recorded_by'] = recorded_by
        else:
            report['recorded_by'] = 'Unknown User'
    return report


def format_for_display(report):
    """
    Format a report for display in web form
    :param report:
    :return:
    """
    report = set_user_name(report)
    report = format_timestamps(report)
    report = format_coordinates(report)
    # Convert all None fields to empty string for display
    display_report = null_to_empty_string(report)
    return display_report


def clean_string(text):
    """
    Removes all linebreaks from a text block
    :param text:
    :return: text with linebreaks removed, strip, excess whitespace
    """
    if type(text) is not str:
        return text

    # Remove linebreaks
    text = text.replace('\r', '').replace('\n', '')
    # Replace multiple whitespace with a single space
    text = re.sub('\s+', ' ', text)
    return text.strip()


def get_diff(report, last_report):
    """
    Get the diff between two versions of a report
    :param report:
    :param last_report:
    :return:
    """
    diff = {}
    for key, value in report.items():
        last_value = last_report.get(key)
        # Compare contents after stripping, removing linebreaks and excess whitespace
        cmp_value = clean_string(value)
        cmp_last_value = clean_string(last_value)
        if cmp_last_value != cmp_value:
            # Change null/empty last values to a string markert
            if not last_value:
                last_value = '(empty)'
            diff[key] = last_value

    # Remove fields that we don't want to diff
    diff.pop('id', None)
    diff.pop('last_updated', None)
    return diff


def get_report_for_display(report_num, ts_url=None):
    """
    Retrieve a spill report and format it for display in an HTML template
    :param report_num:
    :param ts_url:
    :return:
    """

    final_report, last_report = get_report(report_num, ts_url)
    if not final_report:
        return None

    display_report = format_for_display(final_report)
    if last_report:
        # If there is a previous report to compare with, get the diff
        last_report = format_for_display(last_report)
        diff = get_diff(display_report, last_report)
    else:
        # Fixed: Response Activated: Yes is turning itself on when updating a spill report
        # Otherwise set diff to an empty dict
        diff = {}

    # Add attachments
    attachments = get_attachments(report_num)
    display_report['attachments'] = attachments
    display_report['diff'] = diff

    logger.info('Got report: %s' % display_report)
    return display_report


def get_timestamps(report_num):
    """
    Retrieve a list of timestamps for a given spill report
    :param report_num:
    :return:
    """

    timestamps = []
    # Return a copy in human-readable form, another in URL-safe form
    results = db.session.query(
        SpillReport.last_updated).filter(
        SpillReport.report_num == report_num)
    for result in results:
        timestamp = result[0]
        ts_url = timestamp.strftime(settings.filesafe_timestamp)
        ts_display = timestamp.strftime(settings.display_date_fmt)
        ts_ccg_format = timestamp.strftime(settings.ccg_display_fmt)
        timestamps.append({
            'ts': timestamp,
            'ts_url': ts_url,
            'ts_display': ts_display,
            'ts_ccg_format': ts_ccg_format
        })

    logger.info('Report timestamps: %s' % timestamps)
    return timestamps


def current_time_nearest_sec():
    """
    Gets the current time, rounded to the nearest second
    :return:
    """
    d = datetime.now()
    now = d - timedelta(microseconds=d.microsecond)
    return now


def get_attachments(report_num):
    # Get all attachments for this report_num
    attachments = []
    results = AttachedFile.query.filter(
        AttachedFile.report_num == report_num).all()
    for res in results:
        res_dict = result_to_dict(res)
        type = res_dict.get('type')
        file_path = 'report/uploads/%s/%s' % (
                res_dict.get('report_num'), res_dict.get('filename'))
        res_dict['url_path'] = file_path
        if type in settings.IMAGE_FORMATS:
            res_dict['icon_path'] = file_path
        else:
            res_dict['icon_path'] = 'icons/%s.png' % type

        attachments.append(res_dict)
    return attachments


def get_file_extension(filename):
    try:
        extension = os.path.splitext(filename)[1][1:].strip().lower()
        return extension
    except:
        logger.error(traceback.format_exc())
        return ''


def attachments_to_db(report_num, attachments):
    # Create folder for report number
    report_folder = os.path.join(settings.upload_root, report_num)
    os.makedirs(report_folder, exist_ok=True)
    attach_list = []
    for filename in attachments:
        # All attachments will be moved to the report folder LATER.
        extension = get_file_extension(filename)

        attachment_data = {'report_num': report_num,
                       'filename': filename,
                       'type': extension}
        attach_list.append(attachment_data)

    try:
        for attach in attach_list:
            db.session.add(AttachedFile(**attach))
        db.session.commit()
        # If ok, move files here
        for filename in attachments:
            src = os.path.join(settings.attachments, filename)
            dst = os.path.join(report_folder, filename)
            os.rename(src, dst)
    except (SQLAlchemyError, TypeError):
        logger.error(traceback.format_exc())


def save_report_data(report_data):
    """
    Saves a new report, or incremental update of an existing report.
    If there is no report_num, this is a completely NEW report.
    In either case, we simply save all the data as-is.
    :param report_data:
    :return:
    """
    success = False

    # Convert coordinates, if exists
    coordinate_type = report_data.get('coordinate_type')
    coord_str = report_data.get('coordinates')
    if coordinate_type and coord_str:
        # Convert to lat-lon internally
        status, latitude, longitude = coord_converter.convert_to_latlon(
            coordinate_type, coord_str)
        if not status=='OK':
            # Return error message
            return None, success, status

    # Convert timestamps from HTML
    report_date_html = report_data.get('report_date')
    spill_date_html = report_data.get('spill_date')
    if report_date_html:
        report_data['report_date'] = datetime.strptime(
            report_date_html, settings.html_timestamp)
    if spill_date_html:
        report_data['spill_date'] = datetime.strptime(
            spill_date_html, settings.html_timestamp)

    # Convert empty strings to None
    report_data = empty_string_to_null(report_data)

    # Get attachments
    attachments = report_data.get('attachments')

    # Pop unused fields that are only for frontend
    report_data.pop('report_date_html', None)
    report_data.pop('spill_date_html', None)
    report_data.pop('attachments', None)

    # Round off times to nearest second
    now = current_time_nearest_sec()
    report_data['last_updated'] = now

    """
    Auto-generate a polrep number when a new polrep is saved. 
    CREATE SEQUENCE polrepnum START 1;
    SELECT nextval('polrepnum');
    ALTER SEQUENCE polrepnum RESTART WITH 1;
    """
    report_num = report_data.get('report_num')
    report_name = report_data.get('report_name')
    ts = now.strftime(settings.display_date_fmt)

    # Number of versions of this report
    version_count = 0
    if not report_num:
        # This is a New report
        report_num = get_next_polrep_num()
        report_data['report_num'] = report_num
        logger.info('Creating a NEW report with report #: %s' % report_num)

    else:
        # Query DB to get the count
        version_count = db.session.query(SpillReport)\
            .filter(SpillReport.report_num==report_num).count()
        logger.info('There are already %s versions of this report' % version_count)

    logger.info('Updating spill report: %s (%s) at %s' % (
        report_name, report_num, ts))
    try:
        db.session.add(SpillReport(**report_data))
        db.session.commit()
        success = True
        # Update the report map in PostGIS
        postgis_db.update_report_map(report_num)
    except (SQLAlchemyError, TypeError):
        logger.error(traceback.format_exc())

    # Handle attachments
    if attachments:
        attachments_to_db(report_num, attachments)
    report_data['version_count'] = version_count
    return report_data, success, 'OK'


def get_mailing_list_for_report(report_data):
    """
    Choose which mailing list should receive updates to this report, based
    on the report data. For now, we only use the default mailing list.
    :param report_data:
    :return: comma-separated list of recipients
    """
    recipients = notifications.get_maillist_by_name('MAIL_LIST_DEFAULT')
    return recipients


def main():
    list_all_reports()


if __name__ == '__main__':
    main()
