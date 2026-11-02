import numpy as np
from scipy.spatial import cKDTree

from routing.models import FuelStation

BOX_MARGIN_DEGREES = 0.15   # extra room around the route, roughly 10 miles
MILES_PER_DEGREE_LATITUDE = 69.0
MAX_DISTANCE_FROM_ROUTE_MILES = 5.0
def get_stations_in_route_box(route_points):
    """route_points is a list of [longitude, latitude] pairs from OSRM."""
    all_longitudes = [point[0] for point in route_points]
    all_latitudes = [point[1] for point in route_points]

    return FuelStation.objects.filter(
        latitude__gte=min(all_latitudes) - BOX_MARGIN_DEGREES,
        latitude__lte=max(all_latitudes) + BOX_MARGIN_DEGREES,
        longitude__gte=min(all_longitudes) - BOX_MARGIN_DEGREES,
        longitude__lte=max(all_longitudes) + BOX_MARGIN_DEGREES,
    )


def to_flat_miles(longitudes, latitudes, reference_latitude):
    """Turn GPS degrees into x/y positions measured in miles."""
    miles_per_degree_longitude = MILES_PER_DEGREE_LATITUDE * np.cos(np.radians(reference_latitude))
    x_miles = np.asarray(longitudes) * miles_per_degree_longitude
    y_miles = np.asarray(latitudes) * MILES_PER_DEGREE_LATITUDE
    return np.column_stack([x_miles, y_miles])


def get_route_mile_markers(route_flat_miles, total_route_miles):
    """For every route point, how many miles it is from the start."""
    step_lengths = np.hypot(
        np.diff(route_flat_miles[:, 0]),
        np.diff(route_flat_miles[:, 1]),
    )
    miles_from_start = np.concatenate([[0.0], np.cumsum(step_lengths)])
    # the flat grid is slightly approximate, so rescale to OSRM's exact total
    return miles_from_start * (total_route_miles / miles_from_start[-1])


def find_stations_near_route(route_points, total_route_miles):
    """Stations within 5 miles of the road, each with its mile marker."""
    route_longitudes = [point[0] for point in route_points]
    route_latitudes = [point[1] for point in route_points]
    reference_latitude = sum(route_latitudes) / len(route_latitudes)

    route_flat_miles = to_flat_miles(route_longitudes, route_latitudes, reference_latitude)
    route_mile_markers = get_route_mile_markers(route_flat_miles, total_route_miles)

    boxed_stations = list(get_stations_in_route_box(route_points))
    if not boxed_stations:
        return []

    station_flat_miles = to_flat_miles(
        [station.longitude for station in boxed_stations],
        [station.latitude for station in boxed_stations],
        reference_latitude,
    )

    route_tree = cKDTree(route_flat_miles)
    distances, nearest_point_indexes = route_tree.query(
        station_flat_miles,
        distance_upper_bound=MAX_DISTANCE_FROM_ROUTE_MILES,
    )

    stations_near_route = []
    for station, distance, point_index in zip(boxed_stations, distances, nearest_point_indexes):
        if distance > MAX_DISTANCE_FROM_ROUTE_MILES:   # too far: the tree returns infinity
            continue
        stations_near_route.append({
            'opis_id': station.opis_id,
            'name': station.name,
            'city': station.city,
            'state': station.state,
            'price': float(station.price),
            'latitude': station.latitude,
            'longitude': station.longitude,
            'mile_marker': float(route_mile_markers[point_index]),
            'distance_from_route_miles': round(float(distance), 2),
        })
    return keep_cheapest_row_per_station(stations_near_route)

def keep_cheapest_row_per_station(stations):
    """A station can appear on several rows with different prices. Keep the cheapest."""
    cheapest_by_station_id = {}
    for station in stations:
        station_id = station['opis_id']
        is_first_row = station_id not in cheapest_by_station_id
        if is_first_row or station['price'] < cheapest_by_station_id[station_id]['price']:
            cheapest_by_station_id[station_id] = station
    return list(cheapest_by_station_id.values())