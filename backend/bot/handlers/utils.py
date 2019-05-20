import functools

from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler

from bot.mwt import MWT
from core.models import Chat


def get_chat(update) -> Chat:
    return Chat.objects.get_or_create(id=str(update.effective_chat.id))[0]


def handler_decorator_factory(handler_class):
    def handle_decorator(*args, admin_required=False, **kwargs):
        def wrapper(f):
            @functools.wraps(f)
            def dec(update, context):
                if admin_required:
                    if user_is_admin(context.bot, update):
                        return f(update, context)
                    update.message.reply_text("Only admin can use this command.")
                else:
                    return f(update, context)

            dec.handler = handler_class(*args, callback=dec, **kwargs)
            return dec

        return wrapper

    return handle_decorator


command = handler_decorator_factory(CommandHandler)
message_handler = handler_decorator_factory(MessageHandler)
callback_query_handler = handler_decorator_factory(CallbackQueryHandler)


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
