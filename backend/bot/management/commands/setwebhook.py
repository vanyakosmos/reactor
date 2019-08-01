from urllib.parse import urlparse

from django.core.management import BaseCommand

from django.conf import settings
from telegram import Bot


class Command(BaseCommand):
    help = 'If WEBHOOK_URL is specified - setup webhook, otherwise - remove webhook.'

    def handle(self, *args, **options):
        bot = Bot(settings.TG_BOT_TOKEN)
        if settings.WEBHOOK_URL:
            bot.set_webhook(settings.WEBHOOK_URL)
            truncated_hook = urlparse(settings.WEBHOOK_URL).netloc
            self.stdout.write(self.style.SUCCESS(f"Webhook was set up. Host: {truncated_hook}."))
        else:
            bot.delete_webhook()
            self.stdout.write(self.style.WARNING(f"Webhook was removed."))
