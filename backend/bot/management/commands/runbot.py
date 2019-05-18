import logging

from django.conf import settings
from django.core.management import BaseCommand
from telegram.ext import (
    CallbackQueryHandler,
    Filters,
    MessageHandler,
    Updater,
)

from bot.handlers import (
    command_get_buttons,
    command_help,
    command_set_buttons,
    handle_button_callback,
    handle_error,
    handle_message,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start bot.'

    def handle(self, *args, **options):
        updater = Updater(settings.TG_BOT_TOKEN, use_context=True)
        dp = updater.dispatcher

        handlers = [
            command_help,
            command_get_buttons,
            command_set_buttons,
            CallbackQueryHandler(handle_button_callback),
            MessageHandler(Filters.all & ~Filters.status_update.left_chat_member, handle_message),
        ]
        for handler in handlers:
            if hasattr(handler, 'command'):
                handler = handler.command
            dp.add_handler(handler)
        dp.add_error_handler(handle_error)

        print('start polling...')
        updater.start_polling()
        updater.idle()
