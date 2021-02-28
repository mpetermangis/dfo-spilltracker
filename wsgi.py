# WSGI server run by uwsgi / gunicorn
# Must be called 'application', otherwise we get this in uwsgi:
# unable to find "application" callable in file /home/ubuntu/dfo-spilltracker/wsgi.py
from app.app_factory import create_app
import settings

application = create_app()

if __name__ == "__main__":

    # Setup logging
    applog = settings.setup_logger(__name__)

    start_msg = 'Spilltracker backend running from WSGI'
    print(start_msg)
    applog.info(start_msg)

    application.run(
        host="0.0.0.0",
        debug=False,
        log=applog,
        threaded=True
    )
