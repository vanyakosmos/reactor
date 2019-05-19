import logging

from django.conf import settings
from telegram.ext import CallbackQueryHandler, Updater

from .handlers import (
    commands,
    handle_button_callback,
    handle_error,
    handle_message,
    handle_new_member,
    handle_reply,
)

logger = logging.getLogger(__name__)


def run():
    updater = Updater(settings.TG_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    handlers = [
        CallbackQueryHandler(handle_button_callback),
        commands.command_help,
        commands.command_get_buttons,
        commands.command_set_buttons,
        commands.command_credits,
        commands.command_padding,
        commands.command_columns,
        commands.command_allowed,
        commands.command_add_allowed,
        commands.command_remove_allowed,
        handle_reply,
        handle_new_member,
        handle_message,
    ]
    for handler in handlers:
        if hasattr(handler, 'handler'):
            handler = getattr(handler, 'handler')
        dp.add_handler(handler)
    dp.add_error_handler(handle_error)

    logger.info('start polling...')
    updater.start_polling()
    updater.idle()
