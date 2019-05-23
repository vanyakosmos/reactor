import logging

from django.conf import settings
from telegram.ext import Updater, Handler

from .handlers import (
    commands,
    handle_error,
    handle_new_member,
    inline_handlers,
    message_handlers,
    query_callback_handlers,
    replies_handlers,
)

logger = logging.getLogger(__name__)


def extract_by_handler(data_holder):
    res = []
    for key, value in vars(data_holder).items():
        handler = getattr(value, 'handler', None)
        if handler and isinstance(handler, Handler):
            res.append(value)
    return res


def inspect_handlers(handlers: list):
    text = 'Handlers:\n'
    text += '\n'.join([
        f"  > {i + 1:2d}. {handler.__name__:30s} < {handler.__module__}"
        for i, handler in enumerate(handlers)
    ])
    logger.debug(text)


def run():
    updater = Updater(settings.TG_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    handlers = [
        *extract_by_handler(commands),
        *extract_by_handler(query_callback_handlers),
        *extract_by_handler(replies_handlers),
        *extract_by_handler(message_handlers),
        *extract_by_handler(inline_handlers),
        handle_new_member,
    ]
    inspect_handlers(handlers)
    for handler in handlers:
        if hasattr(handler, 'handler'):
            handler = getattr(handler, 'handler')
        dp.add_handler(handler)
    dp.add_error_handler(handle_error)

    logger.info('start polling...')
    updater.start_polling()
    updater.idle()
    logger.info('bye')
