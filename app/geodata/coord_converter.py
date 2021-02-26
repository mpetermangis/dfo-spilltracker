"""
This file contains methods and Flask endpoints to convert
among different coordinate types.
"""

from flask import Blueprint, request, jsonify
import math

# Flask blueprint for geo operations
geo = Blueprint('geo', __name__, url_prefix='/geo')


@geo.route('/latlon_to_coords', methods=['POST'])
def latlon_to_coords():
    data = request.json
    coords = convert_from_latlon(
        data.get('lat'), data.get('lng'))
    return jsonify(success=True, data=coords), 200


@geo.route('/chk_coordinates', methods=['POST'])
def chk_coordinates():
    data = request.json
    coordinate_type = data.get('coordinate_type')
    coord_str = data.get('coord_str')
    status, latitude, longitude = convert_to_latlon(
        coordinate_type, coord_str)
    if not status == 'OK':
        return jsonify(success=False, msg=status), 400
    else:
        data = {'lat': latitude, 'lon': longitude}
        return jsonify(success=True, msg=status, data=data), 200


# Done: convert from latlon to x format when user clicks point on the map, or moves point.
def degree_to_decimal_min(degree_part):
    """
    Converts remainder part of a degree to decimal minutes
    :param degree_part:
    :return:
    """
    return round((degree_part * 60), 6)


def degree_to_ms(degree_part):
    """
    Converts remainder part of a degree to minutes, seconds
    :param degree_part:
    :return:
    """
    (seconds_part, minutes) = math.modf(degree_part * 60)
    seconds = seconds_part * 60
    return minutes, seconds


def coord_to_decimal_and_ms(coord):
    (degree_part, degree_int) = math.modf(coord)
    decimal_min = degree_to_decimal_min(degree_part)
    (minutes, seconds) = degree_to_ms(degree_part)
    return degree_int, decimal_min, int(round(minutes, 0)), int(round(seconds, 0))


def convert_from_latlon(latitude, longitude):
    """
    Converts from lat-lon to coordinates in 3 formats for frontend:
    Decimal Degrees (trivial)
    Degrees Minutes Seconds
    Degrees Decimal Minutes
    :param latitude:
    :param longitude:
    :return:
    """
    (lat_degree, lat_decimal_min, lat_minutes, lat_seconds) = coord_to_decimal_and_ms(latitude)
    (lon_degree, lon_decimal_min, lon_minutes, lon_seconds) = coord_to_decimal_and_ms(longitude)
    decimal_degree = '%s,%s' % (latitude, longitude)
    northing = 'N' if latitude > 0 else 'S'
    easting = 'E' if longitude > 0 else 'W'
    deg_decimal_mins = '%s %s %s %s %s %s' % (
        lat_degree, lat_decimal_min, northing, lon_degree, lon_decimal_min, easting)
    dms = '%s %s %s %s %s %s %s %s' % (
        lat_degree, lat_minutes, lat_seconds, northing,
        lon_degree, lon_minutes, lon_seconds, easting
    )

    print('%s  *   %s   *  %s' % (decimal_degree, deg_decimal_mins, dms))
    coords = {'Decimal Degrees': decimal_degree,
              'Degrees Decimal Minutes': deg_decimal_mins,
              'Degrees Minutes Seconds': dms}
    return coords


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
