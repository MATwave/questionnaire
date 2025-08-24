# survey/management/commands/wait_for_django.py
import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Wait for Django to become ready'

    def handle(self, *args, **options):
        self.stdout.write('Waiting for Django to start...')
        max_retries = 30
        retries = 0

        while retries < max_retries:
            try:
                # Попытка получить главную страницу
                response = requests.get(
                    f'http://localhost:{settings.DJANGO_PORT}/',
                    timeout=1
                )
                if response.status_code < 500:
                    self.stdout.write(self.style.SUCCESS('Django is ready!'))
                    return
            except (requests.ConnectionError, requests.Timeout):
                pass

            retries += 1
            time.sleep(2)

        self.stdout.write(self.style.ERROR('Timed out waiting for Django'))
        exit(1)