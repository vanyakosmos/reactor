from django.core.management import BaseCommand

from bot.main import run


class Command(BaseCommand):
    help = 'Start bot.'

    def handle(self, *args, **options):
        run()
