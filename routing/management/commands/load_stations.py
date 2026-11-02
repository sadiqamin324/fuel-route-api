import csv
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from routing.models import FuelStation

US_STATES = {
    'AL', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'ID', 'IL', 'IN',
    'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT',
    'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA',
    'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
}


class Command(BaseCommand):
    help = "Load fuel stations from CSV: US only, exact duplicate rows removed."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=str(Path(settings.BASE_DIR) / 'data' / 'fuel-prices-for-be-assessment.csv'),
        )

    def handle(self, *args, **opts):
        path = Path(opts['file'])
        if not path.exists():
            raise CommandError(f"CSV not found: {path}")

        seen = set()
        stations = []
        total = exact_dups = non_us = 0

        with open(path, newline='', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                row = {k.strip(): (v or '').strip() for k, v in row.items()}
                total += 1

                key = tuple(row.values())      # all 7 columns
                if key in seen:
                    exact_dups += 1
                    continue
                seen.add(key)

                if row['State'] not in US_STATES:
                    non_us += 1
                    continue

                stations.append(FuelStation(
                    opis_id=int(row['OPIS Truckstop ID']),
                    name=row['Truckstop Name'],
                    address=row['Address'],
                    city=row['City'],
                    state=row['State'],
                    rack_id=int(row['Rack ID']),
                    price=Decimal(row['Retail Price']),
                ))

        FuelStation.objects.all().delete()
        FuelStation.objects.bulk_create(stations, batch_size=1000)

        self.stdout.write(self.style.SUCCESS(
            f"Rows read: {total} | exact duplicates removed: {exact_dups} | "
            f"non-US skipped: {non_us} | saved: {len(stations)}"
        ))