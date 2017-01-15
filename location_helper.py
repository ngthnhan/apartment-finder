import settings
import math
import re
import requests
import json

GMAPS_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
GMAPS_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"

def get_travel_time(src_geocode, dst_geocode, mode="transit"):
    """
    Gets the travel time using Google Maps Directions API.
    :param src_geocode: A tuple of (lat, lon).
    :param dst_geocode: A tuple of (lat, lon).
    :param mode: The mode of transport. Default to "transit".
    :return: The travel time in seconds.
    """
    # Data validation
    if src_geocode is None or dst_geocode is None:
        print("Warning: The source or destination location is not well defined.")
        return 0

    # Prepare the parameters and make a GET requests to the API
    params = {
        'key': settings.GMAPS_API_KEY,
        'origin': '{},{}'.format(src_geocode[0], src_geocode[1]),
        'destination': '{},{}'.format(dst_geocode[0], dst_geocode[1]),
        'mode': mode 
    }
    response = requests.get(GMAPS_DIRECTIONS_URL, params=params)
    results = json.loads(response.text)

    # Return the default value if status returned is not 'OK'
    if results['status'] != 'OK':
        print('Warning: Status is not OK.')
        return -1

    # Get the first route and calculate the total duration
    route = json.loads(response.text)['routes'][0]
    total_duration = 0
    for leg in route['legs']:
        total_duration += leg['duration']['value']
    return total_duration

def get_geocode(location):
    """
    Gets the geocode of the location using Google Maps Geocode API.
    :param location: The string of location.
    :return: A tuple of (lat, lon)
    """
    # Data validation
    if location is None or not location:
        print("Warning: Location is not valid.")
        return (0, 0)
    
    # Create a GET request to the Google Maps API and get the results
    params = {
        "key": settings.GMAPS_API_KEY,
        "address": location
    }
    response = requests.get(GMAPS_GEOCODE_URL, params=params)
    results = json.loads(response.text)

    # Return default value if status returned is not 'OK'
    if results['status'] != 'OK':
        print('Warning: Status is not OK.')
        return (0, 0)

    # Get the first location result from the response
    result = json.loads(response.text)['results'][0]
    location = result['geometry']['location']
    return (location['lat'], location['lng'])

def parse_locations(locations_str):
    """
    Parses the locations string into a list of locations.
    :param locations_str: The string of locations.
    :return: The listing of locations in lowercase.
    """
    # Data validation
    if locations_str is None or not locations_str:
        print("Warning: The locations string is not well defined.")
        return []

    # Parse the locations using special characters
    raw_locations = re.split(r"[^\w\s']", locations_str)

    # Filter out the location that is empty
    locations = []
    for location in raw_locations:
        location = location.strip()
        if location:
            locations.append(location.tolower())

    return locations

def coord_distance(lat1, lon1, lat2, lon2):
    """
    Finds the distance between two pairs of latitude and longitude.
    :param lat1: Point 1 latitude.
    :param lon1: Point 1 longitude.
    :param lat2: Point two latitude.
    :param lon2: Point two longitude.
    :return: Kilometer distance.
    """
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    km = 6367 * c
    return km

def in_box(coords, box):
    """
    Find if a coordinate tuple is inside a bounding box.
    :param coords: Tuple containing latitude and longitude.
    :param box: Two tuples, where first is the bottom left, and the second is the top right of the box.
    :return: Boolean indicating if the coordinates are in the box.
    """
    if box[0][0] < coords[0] < box[1][0] and box[1][1] < coords[1] < box[0][1]:
        return True
    return False

def find_points_of_interest(geotag, location):
    """
    Find points of interest, like transit, near a result.
    :param geotag: The geotag field of a Craigslist result.
    :param location: The where field of a Craigslist result.  Is a string containing a description of where
    the listing was posted.
    :return: A dictionary containing annotations.
    """
    area_found = False
    area = ""
    min_dist = None
    near_bart = False
    bart_dist = "N/A"
    bart = ""
    # Look to see if the listing is in any of the neighborhood boxes we defined.
    for a, coords in settings.BOXES.items():
        if in_box(geotag, coords):
            area = a
            area_found = True

    # Check to see if the listing is near any transit stations.
    for station, coords in settings.TRANSIT_STATIONS.items():
        dist = coord_distance(coords[0], coords[1], geotag[0], geotag[1])
        if (min_dist is None or dist < min_dist) and dist < settings.MAX_TRANSIT_DIST:
            bart = station
            near_bart = True

        if (min_dist is None or dist < min_dist):
            bart_dist = dist

    # If the listing isn't in any of the boxes we defined, check to see if the string description of the neighborhood
    # matches anything in our list of neighborhoods.
    if len(area) == 0:
        for hood in settings.NEIGHBORHOODS:
            if hood in location.lower():
                area = hood

    return {
        "area_found": area_found,
        "area": area,
        "near_bart": near_bart,
        "bart_dist": bart_dist,
        "bart": bart
    }

if "__main__" == __name__:
    src = get_geocode("Downtown Seattle")
    dst = get_geocode("3933 Lake Washington Blvd NE")

    print("Getting the geocode of Downtown Seattle")
    print("Src: ", src)
    print("Dst: ", dst)

    duration = get_travel_time(src, dst)
    print("Result: {} minutes, {} seconds.".format(duration // 60, duration % 60))
