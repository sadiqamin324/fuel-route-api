from django.urls import include, path
from routing.views import FuelRouteView, MapPageView
from routing.views import FuelRouteView

urlpatterns = [
    path('route/', FuelRouteView.as_view(), name='fuel-route'),
     path('map/', MapPageView.as_view(), name='map-page')
]