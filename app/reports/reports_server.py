from flask import Blueprint, flash, jsonify, request, redirect, render_template, url_for, send_file, abort
from flask_security import login_required
from flask_login import current_user
from werkzeug.utils import secure_filename
# import settings
import os
import subprocess
import traceback

from app.reports import excel_export
from app.reports import reports_db as db
from app import settings, lookups, notifications

# import notifications

logger = settings.setup_logger(__name__)

rep = Blueprint('report', __name__, url_prefix='/report')


# All endpoints in this blueprint require user to be logged in
@rep.before_request
def check_login():
    if not current_user:
        return redirect(url_for('security.login'))


# Always add current user to templates for this blueprint
# https://stackoverflow.com/a/26498865
@rep.context_processor
def inject_user():
    return dict(user=current_user)


@rep.route('/')
def reports_all():
    """
    Display a list of all reports, by default sorted reverse chrono
    :return:
    """
    reports_list = db.list_all_reports()
    return render_template('reports_list.html',
                           reports_list=reports_list)


@rep.route('/export/<report_num>/<timestamp>', methods=['GET'])
@rep.route('/export/<report_num>', methods=['GET'])
def export_excel(report_num, timestamp=None):
    # Export to Excel template, with a timestamp version if needed
    report = db.get_report(report_num, timestamp)
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
    # Render the show_report template (a read-only display of a report's state at a given time),
    # along with links to all of the timestamps for this report
    report_timestamps = db.get_timestamps(report_num)
    return render_template('report.html',
                           report=final_report,
                           # marker_drag=False,
                           timestamps=report_timestamps)


@rep.route('/new', methods=['GET'])
def new_report():
    # Display the report form template, keep it blank (no data)
    return render_template('report_form.html',
                           report_num=None,
                           action='New',
                           lookups=lookups.lu,
                           # marker_drag=True,
                           report={})


@rep.route('/<report_num>/update', methods=['GET'])
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
                           # marker_drag=True,
                           report=final_report)


@rep.route('/save_report_data', methods=['POST'])
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
    # report_num = data.get('report_num')
    attachments = save_attachments_to_disk(request)

    # Add attachments before saving to DB
    data['attachments'] = attachments
    data['user_id'] = current_user.id
    spill_id, report_num, success, status = db.save_report_data(data)
    if success:
        logger.info('Saved OK, redirect to show_report: %s' % report_num)
        # Send notification email here
        report_name = data.get('report_name')
        notifications.notify_report_update(report_num, report_name)
        return redirect(url_for('report.show_report', report_num=report_num))
    else:
        resp = jsonify(success=False, msg=status)
    return resp


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
