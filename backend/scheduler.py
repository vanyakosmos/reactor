import django
import schedule
import time

from django.core.management import call_command


def delete_old():
    call_command('deleteold', days=60)


def make_backup():
    call_command('dbbackup')


def main():
    django.setup()
    schedule.every().days.at('00:00').do(make_backup)
    # schedule.every().day.at('01:00').do(delete_old)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    main()
