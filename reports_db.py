
import settings
import os
from datetime import datetime, timedelta
from sqlalchemy import func, create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import psycopg2
import traceback
from geo import coord_converter

engine = create_engine(settings.SPILL_TRACKER_DB_URL)

Base = declarative_base()
Session = sessionmaker()
Session.configure(bind=engine)

logger = settings.setup_logger('reports_db')


# Define database schema
class SpillReport(Base):

    __tablename__ = "spill_reports"

    # Internal fields, not necessarily part of Spill Report schema
    id = Column(Integer,
                primary_key=True,
                nullable=False)
    last_updated = Column(DateTime,
                          nullable=False)
    spill_id = Column(Integer,
                     nullable=False)
    recorded_by = Column(Text,
                       nullable=False)

    # General info
    report_num = Column(Text)
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
    sitation_additional_info = Column(Text)
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


class AttachedFile(Base):

    __tablename__ = "attachments"

    id = Column(Integer,
                primary_key=True,
                nullable=False)
    # spill_id = Column(Integer, ForeignKey('spill_reports.spill_id'))
    spill_id = Column(Integer, nullable=False)
    filename = Column(Text, nullable=False)
    type = Column(Text, nullable=False)


# Create tables
Base.metadata.create_all(engine)


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


def add_html_timestamps(data):
    report_date = data.get('report_date')
    spill_date = data.get('spill_date')
    last_updated = data.get('last_updated')
    data['last_updated_ts'] = last_updated.strftime(settings.filesafe_timestamp)
    if report_date:
        data['report_date_html'] = report_date.strftime(settings.html_timestamp)
    if spill_date:
        data['spill_date_html'] = spill_date.strftime(settings.html_timestamp)
    return data


def list_all_reports():
    """
    Retrieve a summary of all reports.
    (subset of fields for a display snippet) >> NO, get all fields and
    render only the ones we want to display in the *template*
    Get only the latest version of each report.
    Order by last_updated, desc
    :return:
    """
    session = Session()
    results = session.query(SpillReport).all()
    session.close()
    reports_all = {}
    for res in results:
        report = result_to_dict(res)
        # Check if this spill id is already in dict
        spill_id = report.get('spill_id')
        if spill_id not in reports_all:
            reports_all[spill_id] = report
        else:
            # Retrieve existing, compare last updated date, keep newest
            temp_report = reports_all.get(spill_id)
            if report.get('last_updated') > temp_report.get('last_updated'):
                # This version is newer, replace
                reports_all[spill_id] = report
    reports_list = list(reports_all.values())
    reports_list = sorted(reports_list, key=lambda i: i['last_updated'], reverse=True)
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


def get_report(spill_id, ts_url=None):
    """
    Retrieve a spill report at a given timestamp
    :param spill_id:
    :param ts_url: a timestamp in URL-safe format
    :return: spill report as a Python dict
    """
    session = Session()
    if not ts_url:
        # Get the last (most recent version) of this report
        result = session.query(SpillReport).filter(
            SpillReport.spill_id==spill_id).order_by(
            SpillReport.last_updated.desc()).first()

    else:
        # Get update at a specific timestamp
        # Convert ts_url to a timestamp object
        timestamp = datetime.strptime(ts_url, settings.filesafe_timestamp)
        result = session.query(SpillReport).filter(
            SpillReport.spill_id == spill_id,
            SpillReport.last_updated == timestamp).first()

    session.close()

    """
    Most efficient setup is:
    - the latest timestamp for each spill_id should contain the complete representation 
    of the latest spill report. This means that retrieval of any latest spill report is O(1). 
    - in fact, getting any version of any report will be O(1)
    - Whenever a spill report is updated, we simply add a new record with all of the form data 
    (including older versions of some fields that are duplicated, that's fine), and mark it as the 
    latest.  Or do we even need to do that, can we use SQLalchemy to get a last() from a filter?
    - getting the latest version of ALL reports then becomes O(n).  Can probably do it one query, 
    filter the results in regular python, outside of SQLalchemy. 
    """

    final_report = result_to_dict(result)
    return final_report


def get_report_for_display(spill_id, ts_url=None):
    """
    Retrieve a spill report and format it for display in an HTML template
    :param spill_id:
    :param ts_url:
    :return:
    """

    final_report = get_report(spill_id, ts_url)

    # Convert None to empty string for display
    display_report = null_to_empty_string(final_report)
    display_report = add_html_timestamps(display_report)

    # Add attachments
    attachments = get_attachments(spill_id)
    display_report['attachments'] = attachments

    # Add coordinate regex and placeholder
    coord_type = final_report.get('coordinate_type')
    coord_pattern = ''
    coord_placeholder = ''
    coord_help = 'Format: '
    if coord_type == 'Decimal Degrees':
        coord_pattern = '\d{2}\.\d+,-\d{3}\.\d+'
        coord_placeholder = 'XX.XXX,-XXX.XXX'
    elif coord_type == 'Degrees Decimal Minutes':
        coord_pattern = '\d{2} \d{1,2}\.\d+ [Nn] \d{2,3} \d{1,2}\.\d+ [Ww]'
        coord_placeholder = 'XX XX.XXX N XXX XX.XXX W'
    elif coord_type == 'Degrees Minutes Seconds':
        coord_pattern = '\d{2} \d{1,2} \d{1,2} [Nn] \d{2,3} \d{1,2} \d{1,2} [Ww]'
        coord_placeholder = 'XX XX XX N XXX XX XX W'

    display_report['coord_pattern'] = coord_pattern
    display_report['coord_placeholder'] = coord_placeholder
    display_report['coord_help'] = coord_help + coord_placeholder
    logger.info(display_report)
    return display_report


def get_timestamps(spill_id):
    """
    Retrieve a list of timestamps for a given spill report
    :param spill_id:
    :return:
    """
    session = Session()
    timestamps = []
    # Return a copy in human-readable form, another in URL-safe form
    for result in session.query(SpillReport.last_updated).filter(SpillReport.spill_id == spill_id):
        timestamp = result[0]
        ts_url = timestamp.strftime(settings.filesafe_timestamp)
        ts_display = timestamp.strftime(settings.display_date_fmt)
        timestamps.append({'ts': timestamp, 'ts_url': ts_url, 'ts_display': ts_display})
    session.close()
    logger.info(timestamps)
    return timestamps


def current_time_nearest_sec():
    """
    Gets the current time, rounded to the nearest second
    :return:
    """
    d = datetime.now()
    now = d - timedelta(microseconds=d.microsecond)
    return now


def get_attachments(spill_id):
    session = Session()
    # Get all attachments for this spill_id
    attachments = []
    results = session.query(AttachedFile).filter(
        AttachedFile.spill_id == spill_id).all()
    for res in results:
        res_dict = result_to_dict(res)
        type = res_dict.get('type')
        file_path = 'attachments/%s/%s' % (
                res_dict.get('spill_id'), res_dict.get('filename'))
        res_dict['url_path'] = file_path
        if type in settings.IMAGE_FORMATS:
            res_dict['icon_path'] = file_path
        else:
            res_dict['icon_path'] = 'icons/%s.png' % type

        attachments.append(res_dict)
    return attachments


def attachments_to_db(spill_id, attachments):
    # Create folder for spill event
    upload_root = os.path.join(settings.base_dir, 'static', 'attachments')
    spill_folder = os.path.join(upload_root, str(spill_id))
    os.makedirs(spill_folder, exist_ok=True)
    attach_list = []
    for filename in attachments:
        try:
            extension = os.path.splitext(filename)[1][1:].strip().lower()
        except:
            logger.error(traceback.format_exc())
            continue
        attach_data = {'spill_id': spill_id,
                       'filename': filename,
                       'type': extension}
        attach_list.append(attach_data)

    session = Session()
    try:
        for attach in attach_list:
            new_attach = AttachedFile(**attach)
            session.add(new_attach)
        session.commit()
        # If ok, move files here
        for filename in attachments:
            src = os.path.join(upload_root, filename)
            dst = os.path.join(spill_folder, filename)
            os.rename(src, dst)
    except (SQLAlchemyError, TypeError):
        logger.error(traceback.format_exc())
    finally:
        session.close()


def save_report_data(report_data):
    """
    Saves a new report, or incremental update of an existing report.
    If there is no spill_id, this is a completely NEW report.
    In either case, we simply save all the data as-is.
    :param report_data:
    :return:
    """
    success = False
    session = Session()

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

    # TODO: add real users
    report_data['recorded_by'] = 'Default user'

    # Round off times to nearest second
    now = current_time_nearest_sec()
    report_data['last_updated'] = now
    spill_id = report_data.get('spill_id')
    if not spill_id:
        # This is a NEW spill event, increment the next spill ID
        session = Session()
        max_id = session.query(func.max(SpillReport.spill_id)).scalar()
        if not max_id:
            max_id = 0
        spill_id = max_id + 1
        logger.info('New spill report: %s at %s' % (
            spill_id, now.strftime(settings.display_date_fmt)))
        report_data['spill_id'] = spill_id
    else:
        spill_id = int(spill_id.strip())
        report_data['spill_id'] = spill_id
        logger.info('Updating spill report: %s at %s' % (
            spill_id, now.strftime(settings.display_date_fmt)))
    try:
        new_report = SpillReport(**report_data)
        session.add(new_report)
        session.commit()
        success = True
    except (SQLAlchemyError, TypeError):
        logger.error(traceback.format_exc())
    finally:
        session.close()

    # Handle attachments
    if attachments:
        attachments_to_db(spill_id, attachments)
    return spill_id, success, 'OK'


def main():
    list_all_reports()


if __name__ == '__main__':
    main()
