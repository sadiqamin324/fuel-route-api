import requests
from django.core.cache import cache
import hashlib

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving/{coords}"
USER_AGENT = "fuel-route-assessment/1.0 (sadiqamin324@gmail.com)"
METERS_PER_MILE = 1609.344


class RoutingError(Exception):
    pass


def geocode_place(text):
    """'Chicago, IL' -> (lat, lon). Cached, so repeats make no outside call."""
    key = "geo:" + hashlib.md5(text.strip().lower().encode()).hexdigest()
    hit = cache.get(key)
    if hit:
        return hit

    resp = requests.get(
        NOMINATIM_URL,
        params={'q': text, 'format': 'jsonv2', 'countrycodes': 'us', 'limit': 1},
        headers={'User-Agent': USER_AGENT},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise RoutingError(f"Location not found in the USA: {text}")

    result = (float(data[0]['lat']), float(data[0]['lon']))
    cache.set(key, result, 60 * 60 * 24 * 30)
    return result


def get_route(start, end):
    """start, end = (lat, lon). One OSRM call.
    Returns distance in miles and the road path as GeoJSON."""
    coords = f"{start[1]},{start[0]};{end[1]},{end[0]}"   # OSRM wants lon,lat
    resp = requests.get(
        OSRM_URL.format(coords=coords),
        params={'overview': 'full', 'geometries': 'geojson'},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get('code') != 'Ok' or not data.get('routes'):
        raise RoutingError("No driving route found between these locations")

    route = data['routes'][0]
    return {
        'distance_miles': route['distance'] / METERS_PER_MILE,
        'geometry': route['geometry'],       # {'type': 'LineString', 'coordinates': [[lon, lat], ...]}
    }