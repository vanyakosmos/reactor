from django.core.management import BaseCommand

from django.conf import settings
from telegram import Bot


class Command(BaseCommand):
    help = 'If WEBHOOK_URL is specified - setup webhook, otherwise - remove webhook.'

    def handle(self, *args, **options):
        bot = Bot(settings.TG_BOT_TOKEN)
        if settings.WEBHOOK_URL:
            bot.set_webhook(settings.WEBHOOK_URL)
        else:
            bot.delete_webhook()
