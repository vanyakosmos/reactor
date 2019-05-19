import functools

from telegram.ext import CommandHandler, MessageHandler

from bot.mwt import MWT
from core.models import Chat


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


def user_is_admin(bot, update):
    return update.effective_user.id in get_admin_ids(bot, update.message.chat_id)


def bot_is_admin(bot, update):
    return bot.id in get_admin_ids(bot, update.message.chat_id)


def try_delete(bot, update, msg):
    if bot_is_admin(bot, update):
        msg.delete()


def admin_required(f):
    def dec(update, context):
        if user_is_admin(context.bot, update):
            return f(update, context)
        update.message.reply_text("Only admin can use this command.")

    return dec
