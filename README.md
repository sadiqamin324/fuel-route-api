# Fuel Route API

Takes a start and finish in the USA and returns the driving route, the cheapest
fuel stops along it, and the total fuel cost.

## Run it

    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    python manage.py runserver

The included `db.sqlite3` already holds the 7,505 stations with coordinates.

- API: POST http://127.0.0.1:8000/api/route/
  body: {"start": "Los Angeles, CA", "finish": "Chicago, IL"}
- Map page: http://127.0.0.1:8000/api/map/

## Rebuild the data (optional)

    python manage.py load_stations       # loads the CSV
    python manage.py geocode_stations    # adds coordinates (about 1 hour)

## How it works

1. Nominatim (OpenStreetMap) turns the start and finish into coordinates. Cached.
2. OSRM returns the route in one call.
3. Stations inside a box around the route are selected from the database,
   then a KD-tree keeps those within 5 miles of the road and gives each its mile marker.
4. The planner picks the stops (500-mile range, 10 mpg).

Outside calls per request: 1 route call, plus 2 place lookups on a first request.

## Fuel stop rule

At each stop: if a cheaper station is within range, buy only enough fuel to reach it.
Otherwise fill the tank and drive to the cheapest station in range.

## Assumptions

- The vehicle starts with a full tank; only fuel bought along the way is counted.
- Rows identical in all columns are duplicates (26 removed).
- Stations outside the 50 US states (Canadian provinces in the CSV) are excluded.
- Some stations have several prices with no explanation. The lowest price per station is used.
- Station coordinates are at city level (geocoded from city and state), accurate enough
  to decide whether a station is near the route.
- Stations are those within 5 miles of the route.
- Public Nominatim and OSRM servers are used, with their usage limits. OpenRouteService
  would be the fallback.

Map data © OpenStreetMap contributors.
