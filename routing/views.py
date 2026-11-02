import requests
from rest_framework.response import Response
from rest_framework.views import APIView

from routing.services.planner import NoStationInRangeError, plan_fuel_stops
from routing.services.route_client import RoutingError, geocode_place, get_route
from routing.services.stations import find_stations_near_route
from django.views.generic import TemplateView


class FuelRouteView(APIView):
    def post(self, request):
        start_text = request.data.get('start')
        finish_text = request.data.get('finish')
        if not start_text or not finish_text:
            return Response({'error': 'Both "start" and "finish" are required.'}, status=400)

        try:
            start_point = geocode_place(start_text)
            finish_point = geocode_place(finish_text)
            route = get_route(start_point, finish_point)
        except RoutingError as error:
            return Response({'error': str(error)}, status=400)
        except requests.RequestException:
            return Response({'error': 'The map service is unavailable. Please try again.'}, status=502)

        route_points = route['geometry']['coordinates']
        total_miles = route['distance_miles']

        stations_near_route = find_stations_near_route(route_points, total_miles)
        try:
            fuel_plan = plan_fuel_stops(stations_near_route, total_miles)
        except NoStationInRangeError as error:
            return Response({'error': str(error)}, status=422)

        return Response({
            'start': start_text,
            'finish': finish_text,
            'total_distance_miles': round(total_miles, 1),
            'route': route['geometry'],
            'fuel_stops': fuel_plan['fuel_stops'],
            'total_gallons': fuel_plan['total_gallons'],
            'total_fuel_cost': fuel_plan['total_cost'],
            'assumptions': {
                'max_range_miles': 500,
                'miles_per_gallon': 10,
                'starts_with_full_tank': True,
            },
        })

class MapPageView(TemplateView):
        template_name = 'routing/map.html'