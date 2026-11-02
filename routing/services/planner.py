MAX_RANGE_MILES = 500
MILES_PER_GALLON = 10


class NoStationInRangeError(Exception):
    pass


def plan_fuel_stops(stations_near_route, total_route_miles):
    # nearest first; at the same mile, cheapest first
    stations_in_order = sorted(
        stations_near_route,
        key=lambda station: (station['mile_marker'], station['price']),
    )

    current_mile = 0.0
    miles_of_fuel_in_tank = MAX_RANGE_MILES      # starts full
    current_station = None                       # None means we are at the start
    price_here = float('inf')
    fuel_stops = []

    while True:
        furthest_mile_we_can_reach = current_mile + MAX_RANGE_MILES

        if total_route_miles <= furthest_mile_we_can_reach:
            # case 1: the destination is in reach
            next_station = None
            miles_to_buy = max(0, (total_route_miles - current_mile) - miles_of_fuel_in_tank)
        else:
            reachable_stations = [
                station for station in stations_in_order
                if current_mile < station['mile_marker'] <= furthest_mile_we_can_reach
            ]
            if not reachable_stations:
                raise NoStationInRangeError(
                    f"No fuel station within {MAX_RANGE_MILES} miles after mile {current_mile:.0f}"
                )

            cheaper_stations = [s for s in reachable_stations if s['price'] < price_here]
            if cheaper_stations:
                # case 2: buy only enough to reach the nearest cheaper station
                next_station = cheaper_stations[0]
                miles_to_next = next_station['mile_marker'] - current_mile
                miles_to_buy = max(0, miles_to_next - miles_of_fuel_in_tank)
            else:
                # case 3: fill the tank here, go to the cheapest station in reach
                next_station = min(reachable_stations, key=lambda s: s['price'])
                miles_to_buy = MAX_RANGE_MILES - miles_of_fuel_in_tank

        if current_station is not None and miles_to_buy > 0:
            gallons_bought = miles_to_buy / MILES_PER_GALLON
            fuel_stops.append({
                'name': current_station['name'],
                'city': current_station['city'],
                'state': current_station['state'],
                'latitude': current_station['latitude'],
                'longitude': current_station['longitude'],
                'mile_marker': round(current_station['mile_marker'], 1),
                'price_per_gallon': current_station['price'],
                'gallons_bought': round(gallons_bought, 2),
                'cost': round(gallons_bought * current_station['price'], 2),
            })

        miles_of_fuel_in_tank += miles_to_buy

        if next_station is None:
            break                                # we reached the destination

        miles_of_fuel_in_tank -= next_station['mile_marker'] - current_mile
        current_mile = next_station['mile_marker']
        current_station = next_station
        price_here = next_station['price']

    return {
        'fuel_stops': fuel_stops,
        'total_gallons': round(sum(stop['gallons_bought'] for stop in fuel_stops), 2),
        'total_cost': round(sum(stop['cost'] for stop in fuel_stops), 2),
    }