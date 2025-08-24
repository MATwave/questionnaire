import time
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = 'Waits for the database to be available'

    def handle(self, *args, **options):
        self.stdout.write('Waiting for database...')
        db_conn = None
        max_retries = 30
        retries = 0

        while retries < max_retries:
            try:
                db_conn = connections['default']
                db_conn.cursor()
                self.stdout.write(self.style.SUCCESS('Database available!'))
                return
            except OperationalError:
                self.stdout.write('Database unavailable, waiting 1 second...')
                retries += 1
                time.sleep(1)

        self.stdout.write(self.style.ERROR('Max retries reached. Database still not available.'))
        exit(1)