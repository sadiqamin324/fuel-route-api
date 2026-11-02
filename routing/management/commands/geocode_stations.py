import time

import requests
from django.core.management.base import BaseCommand

from routing.models import FuelStation

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "fuel-route-assessment/1.0 (sadiqamin324@gmail.com)"

class Command(BaseCommand):
    help = "Geocode stations by city + state using Nominatim (OpenStreetMap). Safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0,
                            help='Only process this many cities (for testing).')

    def lookup(self, session, city, state):
        params = {
            'q': f"{city}, {state}, USA",
            'format': 'jsonv2',
            'countrycodes': 'us',
            'limit': 1,
        }
        for attempt in range(1, 4):
            try:
                resp = session.get(NOMINATIM_URL, params=params, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    if data:
                        return float(data[0]['lat']), float(data[0]['lon'])
                    return None            # city genuinely not found
                time.sleep(5 * attempt)    # 429 / 5xx: back off and retry
            except requests.RequestException:
                time.sleep(5 * attempt)
        return None

    def handle(self, *args, **opts):
        pairs = list(
            FuelStation.objects.filter(latitude__isnull=True)
            .values_list('city', 'state').distinct().order_by('state', 'city')
        )
        if opts['limit']:
            pairs = pairs[:opts['limit']]

        total = len(pairs)
        self.stdout.write(f"Cities to geocode: {total}")

        session = requests.Session()
        session.headers.update({'User-Agent': USER_AGENT})

        found = 0
        failed = []
        for i, (city, state) in enumerate(pairs, 1):
            coords = self.lookup(session, city, state)
            if coords:
                FuelStation.objects.filter(city=city, state=state).update(
                    latitude=coords[0], longitude=coords[1]
                )
                found += 1
            else:
                failed.append(f"{city}, {state}")

            if i % 50 == 0 or i == total:
                self.stdout.write(f"{i}/{total} done | found {found} | failed {len(failed)}")
            time.sleep(1.1)

        self.stdout.write(self.style.SUCCESS(f"Finished. Found {found}, failed {len(failed)}."))
        if failed:
            self.stdout.write("Not found: " + "; ".join(failed))