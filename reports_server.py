from flask import Blueprint, flash, jsonify, request, redirect, render_template, url_for, send_file, abort
from flask_security import login_required
from flask_login import current_user
from werkzeug.utils import secure_filename
import settings
import os
import subprocess
import traceback
import excel_export
import lookups
import reports_db as db

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


@rep.route('/export/<spill_id>/<timestamp>', methods=['GET'])
@rep.route('/export/<spill_id>', methods=['GET'])
def export_excel(spill_id, timestamp=None):
    # Export to Excel template, with a timestamp version if needed
    report = db.get_report(spill_id, timestamp)
    export_file = excel_export.report_to_excel(report)
    return send_file(export_file,
                     as_attachment=True,
                     attachment_filename=os.path.basename(export_file))


@rep.route('/<spill_id>', methods=['GET'])
@rep.route('/<spill_id>/version/<timestamp>', methods=['GET'])
def show_report(spill_id, timestamp=None):
    """
    Gets either the latest data for a spill report, or from a specific point in time
    :param spill_id:
    :param timestamp:
    :return:
    """
    final_report = db.get_report_for_display(spill_id, timestamp)
    # Render the show_report template (a read-only display of a report's state at a given time),
    # along with links to all of the timestamps for this report
    report_timestamps = db.get_timestamps(spill_id)
    return render_template('report.html',
                           report=final_report,
                           # marker_drag=False,
                           timestamps=report_timestamps)


@rep.route('/new', methods=['GET'])
def new_report():
    # Display the report form template, keep it blank (no data)
    return render_template('report_form.html',
                           spill_id=None,
                           action='New',
                           lookups=lookups.lu,
                           # marker_drag=True,
                           report={})


@rep.route('/<spill_id>/update', methods=['GET'])
def update_report(spill_id):
    """
    Display the report form using the latest incremental data for this spill id
    :param spill_id:
    :return:
    """
    final_report = db.get_report_for_display(spill_id)
    return render_template('report_form.html',
                           spill_id=spill_id,
                           action='Update',
                           lookups=lookups.lu,
                           # marker_drag=True,
                           report=final_report)

@rep.route('/save_report_data', methods=['POST'])
def save_report_data():
    """
    The forms in both /report/new and /report/<spill_id>/update feed to this endpoint
    If it is a NEW report, field spill_id will be blank
    :return:
    """
    # data = request.json
    # Handle files if attached
    attachments = save_attachments(request)
    # Use form data directly, no jQuery
    data = request.form
    if data:
        # If using form data, type will be ImmutableMultiDict. Convert to regular dict
        # https://stackoverflow.com/a/45713753
        data = data.to_dict()

    # Add attachments before saving
    data['attachments'] = attachments
    spill_id, success, status = db.save_report_data(data)
    if success:
        logger.info('Saved OK, redirect to show_report, spill id: %s' % spill_id )
        return redirect(url_for('report.show_report', spill_id=spill_id))
    else:
        resp = jsonify(success=False, msg=status)
    return resp


# Handle file uploads
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in settings.ALLOWED_EXTENSIONS


def save_attachments(request):
    attached = []
    if 'attachments' not in request.files:
        flash('No file part')
        return attached
    # Get multiple files
    files = request.files.getlist('attachments')
    # if user does not select file, browser also
    # submit an empty part without filename
    # if file.filename == '':
    #     flash('No selected file')
    #     return attached
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            attached.append(
                os.path.basename(filename))
    return attached
