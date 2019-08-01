import logging

from telegram.ext import (
    CallbackQueryHandler,
    ChosenInlineResultHandler,
    CommandHandler,
    InlineQueryHandler,
    MessageHandler,
    run_async,
)

from .utils import user_is_admin


class HandlerWrapper:
    def __init__(self, callback, admin_required, handler_class, use_async=False, *args, **kwargs):
        self.func = callback
        self.admin_required = admin_required
        self.handler_class = handler_class
        callback = self.callback
        if use_async:
            callback = run_async(callback)
        self.handler = handler_class(*args, callback=callback, **kwargs)

    @property
    def name(self):
        return self.func.__name__

    @property
    def module(self):
        return self.func.__module__

    def callback(self, update, context):
        logger = logging.getLogger(self.func.__module__)
        logger.debug(f"☎️  CALLING: {self.func.__name__:30s}")
        logger.debug(f"📑\n{update}")
        if self.admin_required:
            if user_is_admin(context.bot, update):
                return self.func(update, context)
            update.message.reply_text("Only admin can use this command.")
        else:
            return self.func(update, context)


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
