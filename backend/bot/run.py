import logging
import re

from django.conf import settings
from telegram.ext import Updater

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


def extract_by_pattern(pattern, data_holder):
    res = []
    p = re.compile(pattern)
    for key, value in vars(data_holder).items():
        if p.match(key):
            res.append(value)
    return res


def run():
    updater = Updater(settings.TG_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    handlers = [
        *extract_by_pattern(r'command_(.+)', commands),
        *extract_by_pattern(r'handle_(.+)', query_callback_handlers),
        *extract_by_pattern(r'handle_(.+)', message_handlers),
        *extract_by_pattern(r'handle_(.+)', replies_handlers),
        *extract_by_pattern(r'handle_(.+)', inline_handlers),
        handle_new_member,
    ]
    for handler in handlers:
        if hasattr(handler, 'handler'):
            handler = getattr(handler, 'handler')
        dp.add_handler(handler)
    dp.add_error_handler(handle_error)

    logger.info('start polling...')
    updater.start_polling()
    updater.idle()
