import functools
import logging

from telegram.ext import (
    CallbackQueryHandler,
    ChosenInlineResultHandler,
    CommandHandler,
    InlineQueryHandler,
    MessageHandler,
    run_async,
)

from . import utils


class HandlerWrapper:
    def __init__(self, func, admin_required, handler_class, use_async=False, *args, **kwargs):
        @functools.wraps(func)
        def callback(update, context):
            logger = logging.getLogger(func.__module__)
            logger.debug(f"☎️  CALLING: {func.__name__:30s}")
            logger.debug(f"📑\n{update}")
            if admin_required:
                if utils.user_is_admin(context.bot, update):
                    return func(update, context)
                update.message.reply_text("Only admin can use this command.")
            else:
                return func(update, context)

        if use_async:
            callback = run_async(callback)

        self.callback = callback
        self.handler_class = handler_class
        self.handler = handler_class(*args, callback=callback, **kwargs)
        self.__doc__ = func.__doc__

    @property
    def name(self):
        return self.callback.__name__

    @property
    def module(self):
        return self.callback.__module__

    def __call__(self, *args, **kwargs):
        self.callback(*args, **kwargs)


def handler_decorator_factory(handler_class, use_async=False):
    def handler_decorator(*args, admin_required=False, **kwargs):
        def decorator(func):
            return HandlerWrapper(func, admin_required, handler_class, use_async, *args, **kwargs)

        return decorator

    return handler_decorator


command = handler_decorator_factory(CommandHandler)
message_handler = handler_decorator_factory(MessageHandler)
callback_query_handler = handler_decorator_factory(CallbackQueryHandler)
inline_query_handler = handler_decorator_factory(InlineQueryHandler)
chosen_inline_handler = handler_decorator_factory(ChosenInlineResultHandler)
