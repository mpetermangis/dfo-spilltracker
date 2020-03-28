from flask import Flask, flash, request, jsonify, send_file, render_template, redirect, url_for, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
import atexit
import settings
import lookups
import reports_db as db
import os
from geo import coord_converter
import exporter

logger = settings.setup_logger(__name__)
port=5000

# app = Flask(__name__, static_folder="attachments")
app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'static/attachments'
# Disable caching on downloaded files
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Disable debug mode on prod



@app.route('/', methods=['GET'])
def index():
    # Redirect to main page
    # user_id = session['user_id']
    # logger.info('User: %s' % user_id)
    return render_template('index.html')


@app.route('/reports', methods=['GET'])
def reports_all():
    """
    Display a list of all reports, by default sorted reverse chrono
    :return:
    """
    reports_list = db.list_all_reports()
    return render_template('reports_list.html',
                           reports_list=reports_list)


@app.route('/export/<spill_id>/<timestamp>', methods=['GET'])
@app.route('/export/<spill_id>', methods=['GET'])
def export_excel(spill_id, timestamp=None):
    # Export to Excel template, with a timestamp version if needed
    report = db.get_report(spill_id, timestamp)
    export_file = exporter.report_to_excel(report)
    return send_file(export_file,
                     as_attachment=True,
                     attachment_filename=os.path.basename(export_file))


@app.route('/report/<spill_id>', methods=['GET'])
@app.route('/report/<spill_id>/<timestamp>', methods=['GET'])
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
                           timestamps=report_timestamps)


@app.route('/report/new', methods=['GET'])
def new_report():
    # Display the report form template, keep it blank (no data)
    return render_template('report_form.html',
                           spill_id=None,
                           action='New',
                           lookups=lookups.lu,
                           report={})


@app.route('/report/<spill_id>/update', methods=['GET'])
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
                           report=final_report)


@app.route('/chk_coordinates', methods=['POST'])
def chk_coordinates():
    data = request.json
    coordinate_type = data.get('coordinate_type')
    coord_str = data.get('coord_str')
    status, latitude, longitude = coord_converter.convert_to_latlon(
        coordinate_type, coord_str)
    if not status == 'OK':
        return jsonify(success=False, msg=status), 400
    else:
        data = {'lat': latitude, 'lon': longitude}
        return jsonify(success=True, msg=status, data=data), 200
    # return resp


@app.route('/save_report_data', methods=['POST'])
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
        return redirect(url_for('show_report', spill_id=spill_id))
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


@app.route('/all_data', methods=['GET'])
def db_dump():
    # Divide db dump by project
    export_file = exporter.dump_all_excel()
    return send_file(export_file,
                     as_attachment=True,
                     attachment_filename=os.path.basename(export_file))


def stop_app():
    logger.info('Shutting down server:  Closing databases...')
    # projdb.close_db()


def main():
    # THIS MAIN METHOD IS ***NOT*** CALLED IF RUNNING FROM WSGI!
    # If running under WSGI, do logging config etc in the WSGI module, not here.

    start_msg = 'Spilltracker Flask server on port %s' % port
    logger.info(start_msg)

    atexit.register(stop_app)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )


if __name__ == '__main__':
    main()


