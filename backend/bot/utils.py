import functools

from telegram.ext import CommandHandler, MessageHandler

from core.models import Chat
from .mwt import MWT


def get_chat(update) -> Chat:
    return Chat.objects.get_or_create(id=str(update.effective_chat.id))[0]


def command(name, *args, **kwargs):
    def wrapper(f):
        @functools.wraps(f)
        def dec(*args2, **kwargs2):
            return f(*args2, **kwargs2)

        dec.handler = CommandHandler(name, dec, *args, **kwargs)
        return dec

    return wrapper


def message_handler(filters, *args, **kwargs):
    def wrapper(f):
        @functools.wraps(f)
        def dec(*args2, **kwargs2):
            return f(*args2, **kwargs2)

        dec.handler = MessageHandler(filters, dec, *args, **kwargs)
        return dec

    return wrapper


@MWT(timeout=60 * 60)
def get_admin_ids(bot, chat_id):
    """Returns a list of admin IDs for a given chat. Results are cached for 1 hour."""
    return [admin.user.id for admin in bot.get_chat_administrators(chat_id)]


def bot_is_admin(bot, update):
    return bot.id in get_admin_ids(bot, update.message.chat_id)