import logging
from typing import List

from django.conf import settings
from telegram.ext import (
    Updater,
    Dispatcher,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    InlineQueryHandler,
    ChosenInlineResultHandler,
)

from .core import handle_error
from . import channel_publishing, channel_reaction, core, group_reaction, group_reposting
from .wrapper import HandlerWrapper

logger = logging.getLogger(__name__)


def extract_handlers(module):
    res = []
    for key, value in vars(module).items():
        if isinstance(value, HandlerWrapper):
            res.append(value)
    return res


def inspect_handlers(handlers: List[HandlerWrapper]):
    text = 'Handlers:\n'
    text += '\n'.join([
        f"  > {i + 1:2d}. {handler.module:40s} > {handler.name}"
        for i, handler in enumerate(handlers)
    ])
    logger.debug(text)


def sort_by_type(handlers: List[HandlerWrapper]):
    """
    0 commands
    1 query callback handlers
    2 message handlers
    3 inline results handlers
    4 inline respond handlers
    """
    priority = dict(
        map(
            lambda e: (e[1], e[0]),
            enumerate([
                CommandHandler,
                CallbackQueryHandler,
                MessageHandler,
                InlineQueryHandler,
                ChosenInlineResultHandler,
            ])
        )
    )
    handlers.sort(key=lambda h: priority[h.handler_class])


def setup_dispatcher(dp: Dispatcher, inspect=True):
    handlers = []
    for module in [channel_publishing, channel_reaction, core, group_reaction, group_reposting]:
        handlers.extend(extract_handlers(module))

    sort_by_type(handlers)
    for wrapper in handlers:
        dp.add_handler(wrapper.handler)
    dp.add_error_handler(handle_error)
    if inspect:
        inspect_handlers(handlers)


def run():
    updater = Updater(settings.TG_BOT_TOKEN, use_context=True)
    setup_dispatcher(updater.dispatcher)

    logger.info('start polling...')
    updater.start_polling()
    updater.idle()
    logger.info('bye')
