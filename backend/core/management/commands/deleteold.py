from datetime import timedelta

from django.core.management import BaseCommand

from core.models import Message, MessageToPublish


class Command(BaseCommand):
    help = 'Delete old messages and staled message-to-publish.'

    def add_arguments(self, parser):
        parser.add_argument('-d', '--days', type=int, default=30)

    def handle(self, *args, **options):
        days = options.get('days')
        self.stdout.write(f"Deleting messages over {days} days old.")
        delta = timedelta(days=days)
        a = Message.objects.delete_old(delta)
        b = MessageToPublish.objects.delete_old(delta)
        self.stdout.write(self.style.SUCCESS(f"Deleted {a} messages and {b} messages-to-publish."))
