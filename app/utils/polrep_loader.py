from openpyxl import load_workbook
import os
import settings
from datetime import datetime

logger = settings.setup_logger(__name__)


def open_legacy_file(path):
    book = load_workbook(path)
    return book


def fix_2017_format(report_num):
    rep_num = report_num.replace('-2017', '')
    return '2017-%s' % rep_num


def load_data_all(legacy_file):
    logger.info('Opening: %s' % legacy_file)
    book = open_legacy_file(legacy_file)
    for year in ['2017', '2018', '2019']:
        load_data_year(year, book)


def load_data_year(year, book):

    logger.info('POLREPS for %s...' % year)
    year_ws = book[year]
    for row in year_ws.iter_rows(min_row=2):  # , max_row=2
        report_num = row[0].value
        if report_num is None:
            # Probably end of the table
            logger.warning('Probably end of the table? but openpyxl goes over a few rows...')
            continue

        # Fix 2017 report format
        if year == '2017':
            report_num = fix_2017_format(report_num)

        report_name = row[1].value
        report_label = 'Report: %s, %s' % (report_num, report_name)
        # date comes in as a datetime object with 00:00 timestamp
        spill_date = row[2].value
        # time is a string, need to add to date
        time_str = row[3].value
        # Try to parse as datetime if not null, and not already a datetime

        TIME_SHORT = '%H:%M'
        TIME_LONG = '%H:%M:%S'
        TIME_AMPM = '%I:%M:%S %p'
        if time_str:
            # Default: assume time_str was parsed as datetime.time
            time = time_str
            if type(time_str) is str:

                time_format = TIME_SHORT
                if 'am' in time_str.lower() or 'pm' in time_str.lower():
                    time_format = TIME_AMPM
                if time_str.count(':') == 2:
                    time_format = TIME_LONG

                # Try to parse as datetime
                try:
                    time = datetime.strptime(time_str, time_format).time()
                except (ValueError, TypeError):
                    logger.error('%s: Very Bad timestamp: %s' % (
                        report_label, time_str))
                    time = None

                # try:
                #     time = datetime.strptime(time_str, '%H:%M').time()
                # except (ValueError, TypeError):
                #     # Try with seconds
                #     try:
                #         time = datetime.strptime(time_str, '%H:%M:%S').time()
                #     except (ValueError, TypeError):
                #         logger.error('%s: Very Bad timestamp: %s' % (
                #             report_label, time_str))
                #         time = None
            # elif type(time_str) is datetime:
            #     logger.warning('Time column is already a datetime object!')
            #     time = time_str
            # else:
            #     logger.warning('Unknown data type in time column! %s' % time_str)
            #     time = None
            # logger.error('%s: Bad timestamp: %s' % (
            #     report_label, time_str))
            # continue
        else:
            logger.warning('Time field is null/empty')
            time = None

        # Update date with hour and minute
        if type(spill_date) is datetime and time is not None:
            try:
                spill_date = spill_date.replace(hour=time.hour, minute=time.minute)
            except:
                logger.warning('Time is empty or invalid')


        vessel_name = row[4].value
        pollutant_details = row[5].value
        pollutant = row[6].value

        # Get latitude, longitude, check type
        latitude = row[7].value  # float
        longitude = row[8].value  # float
        try:
            latitude = float(latitude)
        except:
            logger.error('%s: Invalid latitude: "%s" ' % (report_label, latitude))
            latitude = None

        try:
            longitude = float(longitude)
        except:
            logger.error('%s: Invalid longitude: "%s" ' % (report_label, longitude))
            longitude = None

        # if type(latitude) is not float:
        #     logger.error('%s: Invalid latitude: "%s" ' % (report_label, latitude))
        #     latitude = None
        # if type(longitude) is not float:
        #     logger.error('%s: Invalid longitude: "%s" ' % (report_label, longitude))
        #     longitude = None

        additional_info = row[9].value
        er_region = row[10].value
        response_activated = row[11].value
        fleet_tasking = row[12].value
        station_or_ship = row[13].value
        unit = row[14].value

        logger.info('%s %s %s %s' % (report_num, report_name, spill_date, time_str))
        # logger.info(report_num)

        # for cell in row:
        #     print(cell.value)


def main():
    legacy = os.path.join(settings.upload_root, '2021-02-11_Legacy_Polreps.xlsx')
    # open_legacy_file(legacy)
    # load_data_year('2017', legacy)
    load_data_all(legacy)


if __name__ == '__main__':
    main()
