import logging

from telegram.ext import (
    CallbackQueryHandler,
    ChosenInlineResultHandler,
    CommandHandler,
    InlineQueryHandler,
    MessageHandler,
)

from core.models import Chat
from .utils import user_is_admin


def get_chat(update) -> Chat:
    return Chat.objects.get_or_create(id=str(update.effective_chat.id))[0]


class HandlerWrapper:
    def __init__(self, callback, admin_required, handler_class):
        self.callback = callback
        self.admin_required = admin_required
        self.handler_class = handler_class
        self.handler = None

    @property
    def name(self):
        return self.callback.__name__

    @property
    def module(self):
        return self.callback.__module__

    def __call__(self, update, context):
        logger = logging.getLogger(self.callback.__module__)
        logger.debug(f"☎️  CALLING: {self.callback.__name__:30s}")
        logger.debug(f"📑\n{update}")
        if self.admin_required:
            if user_is_admin(context.bot, update):
                return self.callback(update, context)
            update.message.reply_text("Only admin can use this command.")
        else:
            return self.callback(update, context)


def handler_decorator_factory(handler_class):
    def handler_decorator(*args, admin_required=False, **kwargs):
        def decorator(func):
            wrapper = HandlerWrapper(func, admin_required, handler_class)
            wrapper.handler = handler_class(*args, callback=wrapper, **kwargs)
            return wrapper

        return decorator

    return handler_decorator


command = handler_decorator_factory(CommandHandler)
message_handler = handler_decorator_factory(MessageHandler)
callback_query_handler = handler_decorator_factory(CallbackQueryHandler)
inline_query_handler = handler_decorator_factory(InlineQueryHandler)
chosen_inline_handler = handler_decorator_factory(ChosenInlineResultHandler)
