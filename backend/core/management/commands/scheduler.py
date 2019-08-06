import time

import schedule
from django.core.management import BaseCommand, call_command


def delete_old():
    call_command('deleteold', days=60)


def make_backup():
    call_command('dbbackup')


class Command(BaseCommand):
    help = 'Delete old messages and staled message-to-publish.'

    def add_arguments(self, parser):
        parser.add_argument('--backup', action='store_true')
        parser.add_argument('--clean-up', action='store_true')

    def handle(self, *args, **options):
        backup = options.get('backup')
        clean_up = options.get('clean_up')

        if backup:
            j = schedule.every().days.at('00:00').do(make_backup)
            self.stdout.write(f"Scheduled backup: {j}.")
        if clean_up:
            j = schedule.every().day.at('01:00').do(delete_old)
            self.stdout.write(f"Scheduled clean up: {j}.")
        if len(schedule.jobs) == 0:
            self.stdout.write(self.style.ERROR(f"Nothing was scheduled."))
            return

        while True:
            schedule.run_pending()
            time.sleep(1)
