import logging

from django.conf import settings
from telegram.ext import CallbackQueryHandler, Updater

from .handlers import (
    command_get_buttons,
    command_help,
    command_set_buttons,
    handle_button_callback,
    handle_error,
    handle_message,
    handle_new_member,
)

logger = logging.getLogger(__name__)


def run():
    updater = Updater(settings.TG_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    handlers = [
        CallbackQueryHandler(handle_button_callback),
        command_help,
        command_get_buttons,
        command_set_buttons,
        handle_new_member,
        handle_message,
    ]
    for handler in handlers:
        if hasattr(handler, 'handler'):
            handler = getattr(handler, 'handler')
        dp.add_handler(handler)
    dp.add_error_handler(handle_error)

    print('start polling...')
    updater.start_polling()
    updater.idle()
