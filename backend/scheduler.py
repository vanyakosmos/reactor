import sys

import django
import schedule
import time

from django.core.management import call_command


def delete_old():
    call_command('deleteold', days=60)


def make_backup():
    call_command('dbbackup')


def run(backup=False, clean_up=False):
    django.setup()
    if backup:
        schedule.every().days.at('00:00').do(make_backup)
    if clean_up:
        schedule.every().day.at('01:00').do(delete_old)
    if not any([backup, clean_up]):
        return

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    run(
        backup='backup' in sys.argv,
        clean_up='clean_up' in sys.argv,
    )
