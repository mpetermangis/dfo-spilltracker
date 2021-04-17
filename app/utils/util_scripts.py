import sys
sys.path.extend(['/home/spill/spilltracker'])

from app.utils import polrep_loader
import os
import settings


logger = settings.setup_logger(__name__)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--legacy', action='store_true',
                        help='Load legacy POLREPs from settings.upload_root')
    legacy_file = os.path.join(settings.upload_root, '2021-02-11_Legacy_Polreps.xlsx')

    args = parser.parse_args()
    if args.legacy:
        polrep_loader.load_data_all(legacy_file)

    logger.warning('No option selected.')


if __name__ == '__main__':
    main()
