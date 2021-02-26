from app import settings
from app.app_factory import create_app

logger = settings.setup_logger(__name__)
port = 5000


def main():
    # THIS MAIN METHOD IS ***NOT*** CALLED IF RUNNING FROM WSGI!
    # If running under WSGI, do logging config etc in the WSGI module, not here.
    # ONLY FOR LOCAL DEVELOPMENT

    start_msg = 'Spilltracker DEVELOPMENT Flask server on port %s' % port
    logger.info(start_msg)

    # atexit.register(stop_app)

    app = create_app()

    app.run(
        # host="0.0.0.0",
        host="localhost",
        port=port,
        ssl_context='adhoc',
        debug=True
    )


if __name__ == '__main__':
    main()
