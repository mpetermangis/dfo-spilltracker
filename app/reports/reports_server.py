import os
from datetime import datetime
from flask import Blueprint, flash, jsonify, request, redirect, render_template, url_for, send_file, send_from_directory
from flask_login import current_user
from flask_security import roles_required
from werkzeug.utils import secure_filename

import settings
from app.reports import excel_export
from app.reports import reports_db as db
from app.reports.reports_db import SpillReport
from app.utils import notifications, lookups
from app.geodata import postgis_db


logger = settings.setup_logger(__name__)

rep = Blueprint('report', __name__, url_prefix='/report')
                # static_url_path='/report/uploads',
                # static_folder=settings.upload_root)


# All endpoints in this blueprint require user to be logged in
@rep.before_request
def check_login():
    if not current_user:
        return redirect(url_for('security.login'))


@rep.route('/')
def reports_all():
    """
    Display a list of all reports, by default sorted reverse chrono
    :return:
    """
    reports_list = db.list_all_reports()
    return render_template('reports_list.html',
                           reports_list=reports_list)


@rep.route('/uploads/<report_num>/<path:filename>')
def serve_attachments(report_num, filename):
    fulldir = os.path.join(settings.upload_root,
                            report_num)
    logger.info('Serving attachment: %s, %s' % (fulldir, filename))
    return send_from_directory(fulldir, filename)


def add_leaflet_popups(mapview_reports):
    """
    Adds a rendered leaflet popup to each mapview report item
    :param mapview_reports:
    :return:
    """
    reports = []
    for spill in mapview_reports:
        # Add rendered popup for Leaflet
        spill = db.null_to_empty_string(spill)
        spill['popup'] = render_template('snippets/_report_map_sample.html',
                                         spill=spill)
        reports.append(spill)
    return reports


@rep.route('/map', methods=['GET'])
def reports_map():
    return render_template('reports_map.html')


@rep.route('/map_search', methods=['POST'])
def reports_map_search():
    data = request.json
    mapview_reports = postgis_db.get_reports_bbox(
        data.get('lon_min'), data.get('lat_min'),
        data.get('lon_max'), data.get('lat_max')
    )
    mapview_reports = add_leaflet_popups(mapview_reports)
    return jsonify(success=True, data=mapview_reports), 200


@rep.route('/render_map_samples', methods=['POST'])
def render_map_samples():
    spills = request.json
    spills_display = []
    for sp in spills:
        spills_display.append(db.null_to_empty_string(sp))
    rendered = render_template('snippets/_report_map_samples_all.html',
                               spills=spills_display)
    logger.info('Rendered %s report samples' % len(spills))
    return jsonify(success=True, data=rendered), 200


@rep.route('/search/<query_text>', methods=['GET'])
def report_search(query_text):
    logger.info('Searching text: %s' % query_text)
    results = SpillReport.query.search(query_text, limit=10).all()
    if len(results) is None:
        logger.warning('No search results')
    for result in results:
        print(str(result))
    return 'Search results: %s' % ', '.join(str(r) for r in results)


@rep.route('/export/<report_num>/<timestamp>', methods=['GET'])
@rep.route('/export/<report_num>', methods=['GET'])
def export_excel(report_num, timestamp=None):
    # Export to Excel template, with a timestamp version if needed
    report, last_report = db.get_report(report_num, timestamp)
    export_file = excel_export.report_to_excel(report)
    return send_file(export_file,
                     as_attachment=True,
                     attachment_filename=os.path.basename(export_file))


@rep.route('/<report_num>', methods=['GET'])
@rep.route('/<report_num>/version/<timestamp>', methods=['GET'])
def show_report(report_num, timestamp=None):
    """
    Gets either the latest data for a spill report, or from a specific point in time
    :param report_num:
    :param timestamp:
    :return:
    """
    final_report = db.get_report_for_display(report_num, timestamp)
    if final_report is None:
        # Report number was not found, go to 404 page
        return render_template('404.html')
    # Render the show_report template (a read-only display of a report's state at a given time),
    # along with links to all of the timestamps for this report
    report_timestamps = db.get_timestamps(report_num)
    return render_template('report.html',
                           report=final_report,
                           timestamps=report_timestamps)


@rep.route('/new', methods=['GET'])
# If a list of role names is specified here, the user mast have
# any one of the specified roles to gain access.
# https://flask-user.readthedocs.io/en/latest/authorization.html
@roles_required(['admin', 'user'])
def new_report():

    # Display the report form template, keep it blank (no data)
    # Set default report date to current date
    report_date = datetime.now().strftime(settings.html_timestamp)
    report = {'report_date_html': report_date}
    return render_template('report_form.html',
                           report_num=None,
                           report=report,
                           action='New',
                           lookups=lookups.lu
                           )


@rep.route('/<report_num>/update', methods=['GET'])
@roles_required(['admin', 'user'])
def update_report(report_num):
    """
    Display the report form using the latest incremental data for this spill id
    :param report_num:
    :return:
    """
    final_report = db.get_report_for_display(report_num)
    return render_template('report_form.html',
                           report_num=report_num,
                           action='Update',
                           lookups=lookups.lu,
                           report=final_report)


@rep.route('/save_report_data', methods=['POST'])
@roles_required(['admin', 'user'])
def save_report_data():
    """
    The forms in both /report/new and /report/<report_num>/update feed to this endpoint
    If it is a NEW report, field report_num will be blank
    :return:
    """

    # Use form data directly, no jQuery
    data = request.form
    if data:
        # If using form data, type will be ImmutableMultiDict. Convert to regular dict
        # https://stackoverflow.com/a/45713753
        data = data.to_dict()

    # Handle files if attached
    attachments = save_attachments_to_disk(request)

    # Add attachments and user id before saving to DB
    data['attachments'] = attachments
    data['user_id'] = current_user.id
    report_data, success, status = db.save_report_data(data)
    report_num = report_data.get('report_num')
    if success:
        logger.info('Saved OK, redirect to show_report: %s' % report_num)

        # Send notification email here
        msg_content, msg_subject = prepare_report_email(report_data)
        notifications.notify_report(msg_content, msg_subject)
        return redirect(url_for('report.show_report', report_num=report_num))
    else:
        resp = jsonify(success=False, msg=status)
    return resp


def prepare_report_email(report):
    """
    Render the HTML email subject line and content for an update message.
    :param report_num:
    :param report_name:
    :return: rendered HTML
    """
    msg_content = render_template('report_email.html', report=report)
    version_count = report.get('version_count')
    report_num = report.get('report_num')
    report_name = report.get('report_name')
    if version_count > 0:
        # This is an update
        msg_subject = 'UPDATE #%s - %s - %s' % (
            version_count, report_num, report_name)
    else:
        # This is a new report
        msg_subject = '%s - %s' % (report_num, report_name)
    return msg_content, msg_subject


# Handle file uploads
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in settings.ALLOWED_EXTENSIONS


def save_attachments_to_disk(request):
    attached = []
    if 'attachments' not in request.files:
        flash('No file part')
        return attached

    # Create folder for uploads if needed
    # report_uploads = os.path.join(settings.upload_folder, report_num)
    # os.makedirs(report_uploads, exist_ok=True)

    # Get multiple files
    files = request.files.getlist('attachments')
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(settings.attachments, filename))
            attached.append(
                os.path.basename(filename))
    logger.info('Saved attachments: %s' % attached)
    return attached


# Export all reports to Excel
@rep.route('/all_data', methods=['GET'])
def db_dump():
    # Divide db dump by project
    export_file = excel_export.dump_all_excel()
    return send_file(export_file,
                     as_attachment=True,
                     attachment_filename=os.path.basename(export_file))
