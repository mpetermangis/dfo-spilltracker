from sqlalchemy import create_engine
import settings

logger = settings.setup_logger(__name__)

engine = create_engine(settings.SPILL_TRACKER_DB_URL)

REPORT_SRID = 4326


# Create view for spill reports with PostGIS geom
def create_map_view():
    logger.info('Creating report_map_view...')
    engine.execute('DROP VIEW IF EXISTS report_map_view;')
    engine.execute(''' CREATE VIEW report_map_view AS
    SELECT DISTINCT ON (report_num) ST_SetSRID( ST_Point( longitude, latitude), %s) AS geometry, 
    * FROM public.spill_reports
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    ORDER BY report_num, last_updated DESC;
    ''' % REPORT_SRID)


def update_report_map(report_num):
    # Update report_map_tbl when a spill report is updated
    # Delete and insert the latest record for a given report_num
    logger.info('Updating report map table: %s' % report_num)
    sql_delete = "delete from report_map_tbl where report_num='%s';" % report_num
    engine.execute(sql_delete)
    sql_insert = """ insert into report_map_tbl 
                    select * from report_map_view rmv 
                    where report_num='%s'
                    """ % report_num
    engine.execute(sql_insert)


# Get spill reports using a bounding box and other params
# def get_reports_bbox(lon_min, lat_min, lon_max, lat_max):
def get_reports_bbox(data):
    (lon_min, lat_min, lon_max, lat_max) = (
        data.get('lon_min'), data.get('lat_min'),
        data.get('lon_max'), data.get('lat_max'))
    if type(lon_min) is not float or type(lat_min) is not float or type(lon_max) is not float or type(lat_max) is not float:
        logger.error('Bad lat-lon bbox!')
        return []

    date_from = data.get('date_from')
    date_to = data.get('date_to')

    # Bbox query in postgis: https://gis.stackexchange.com/a/83448
    param_list = []
    full_query = """
    SELECT *
    FROM   report_map_tbl
    WHERE  geometry 
        -- && -- intersects,  gets more rows  -- CHOOSE ONLY THE
        @ -- contained by, gets fewer rows -- ONE YOU NEED!
        ST_MakeEnvelope (
            %s, %s, -- bounding 
            %s, %s, -- box limits
            %s)
    """

    param_list = [lon_min, lat_min, lon_max, lat_max, REPORT_SRID]

    if date_from and date_to:
        full_query += ' AND spill_date BETWEEN %s AND %s'
        param_list.append(date_from)
        param_list.append(date_to)
        # date_from, date_to)

    full_query += ' order by last_updated desc ;'
    params = tuple(param_list)

    reports = engine.execute(full_query, params)
    # Return only the info needed to render the map view
    mapview_reports = []
    for r in reports:

        r_mapview = {
            'report_num': r.report_num,
            'report_name': r.report_name,
            'pollutant': r.pollutant,
            'quantity': r.quantity,
            'quantity_units': r.quantity_units,
            'latitude': r.latitude,
            'longitude': r.longitude
        }

        logger.debug('Got report: %s' % r_mapview)
        mapview_reports.append(r_mapview)

    logger.info('There are %s reports in this Bbox' % len(mapview_reports))
    return mapview_reports


def main():
    # test getting reports by bbox
    get_reports_bbox(-123.098, 49.0, -123.0, 49.141)


if __name__ == '__main__':
    main()
