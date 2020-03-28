"""
This file contains methods to convert among different coordinate types
"""


def convert_to_latlon(coordinate_type, coord_str):
    """
    Convert a coordinate string to lat-lon
    :param coordinate_type: type indicator
    :param coord_str: coordinate string
    :return: status message, latitude, longitude
    """
    status = 'OK'
    latitude = None
    longitude = None
    if coordinate_type == 'Decimal Degrees':
        # XX.XXX,-XX.XXX
        coord_str = coord_str.strip()
        coords = coord_str.split(',')
        if not len(coords) == 2:
            return 'Invalid Decimal Degrees: %s' % coord_str, None, None
        try:
            latitude = float(coords[0])
            longitude = float(coords[1])
        except (TypeError, ValueError):
            return 'Invalid coordinate: %s' % coord_str, None, None

    elif coordinate_type == 'Degrees Minutes Seconds':
        # XX XX XX N XXX XX XX W
        north_parts, west_parts, north, west = split_north_west_parts(coord_str)
        north_degrees = dms_to_degree(north_parts)
        west_degrees = dms_to_degree(west_parts)
        if not north_degrees:
            return 'Invalid DMS northing: %s' % north, None, None
        if not west_degrees:
            return 'Invalid DMS west: %s' % west, None, None
        # Convert west to negative
        west_degrees = -1 * west_degrees
        latitude = north_degrees
        longitude = west_degrees

    elif coordinate_type == 'Degrees Decimal Minutes':
        north_parts, west_parts, north, west = split_north_west_parts(coord_str)
        north_degrees = decimal_min_to_degree(north_parts)
        west_degrees = decimal_min_to_degree(west_parts)
        if not north_degrees:
            return 'Invalid Degree Decimal Min northing: %s' % north, None, None
        if not west_degrees:
            return 'Invalid Degree Decimal Min west: %s' % west, None, None
        # Convert west to negative
        west_degrees = -1 * west_degrees
        latitude = north_degrees
        longitude = west_degrees

    # Check lat-lon within range
    if not -180 <= longitude <= 180:
        return 'Longitude must be between -180, 180 degrees (value: %s)' % longitude, None, None
    if not -90 <= latitude <= 90:
        return 'Latitude must be between -90, 90 degrees (value: %s)' % latitude, None, None

    # Should be ok
    return status, latitude, longitude


def dms_to_degree(parts):
    if not len(parts) == 3:
        return False
    d = parts[0].strip()
    min = parts[1].strip()
    sec = parts[2].strip()
    try:
        d = int(d)
        min = int(min)
        sec = int(sec)
    except (TypeError, ValueError):
        return False
    decimal_degree = d + (min / 60) + (sec / 3600)
    return decimal_degree


def decimal_min_to_degree(parts):

    if not len(parts) == 2:
        return False
    d = parts[0].strip()
    min = parts[1].strip()
    try:
        d = int(d)
        min = float(min)
    except (TypeError, ValueError):
        return False
    decimal_degree = d + (min / 60)
    return decimal_degree


def split_north_west_parts(coord_str):
    """
    Splits a coordinate containing N and W to the north and west components
    :param coord_str:
    :return:
    """
    coord_str = coord_str.lower().strip()
    coords = coord_str.split('n')
    north = coords[0].strip()
    west = coords[1].replace('w', '').strip()
    north_parts = north.split(' ')
    west_parts = west.split(' ')
    return north_parts, west_parts, north, west
