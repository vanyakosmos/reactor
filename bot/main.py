import logging
import os

import django
from django.conf import settings
from telegram.ext import (
    CallbackQueryHandler,
    Filters,
    MessageHandler,
    Updater,
)

logger = logging.getLogger(__name__)


def setup():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.reactor.settings')
    django.setup()


def main():
    from bot.handlers import (
        command_help,
        command_get_buttons,
        command_set_buttons,
        handle_button_callback,
        handle_message,
        handle_error,
    )

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


if __name__ == '__main__':
    setup()
    main()
