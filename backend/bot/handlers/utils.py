import functools
import logging

from django.utils.datastructures import OrderedSet
from emoji import UNICODE_EMOJI
from telegram import Update, Message as TGMessage, Chat as TGChat, User as TGUser
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    ChosenInlineResultHandler,
)

from bot.handlers.consts import MESSAGE_TYPES
from bot.mwt import MWT
from bot.redis import save_media_group
from core.models import Chat, User


def get_chat(update) -> Chat:
    return Chat.objects.get_or_create(id=str(update.effective_chat.id))[0]


def handler_decorator_factory(handler_class):
    def handle_decorator(*args, admin_required=False, **kwargs):
        def wrapper(f):
            @functools.wraps(f)
            def dec(update, context):
                logger = logging.getLogger(dec.__module__)
                logger.debug(f"☎️  CALLING: {dec.__name__:30s}")
                logger.debug(f"📑\n{update}")
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
inline_query_handler = handler_decorator_factory(InlineQueryHandler)
chosen_inline_handler = handler_decorator_factory(ChosenInlineResultHandler)


@MWT(timeout=60)
def get_admin_ids(bot, chat_id):
    """Returns a set of admin IDs for a given chat. Results are cached for 1 minute."""
    return {admin.user.id for admin in bot.get_chat_administrators(chat_id)}


def user_is_chat_admin(bot, user_id, chat_id):
    return user_id in get_admin_ids(bot, chat_id)


def user_is_admin(bot, update: Update):
    return user_is_chat_admin(bot, update.effective_user.id, update.effective_chat.id)


def bot_is_admin(bot, update):
    return user_is_chat_admin(bot, bot.id, update.effective_chat.id)


def try_delete(bot, update, msg):
    if bot_is_admin(bot, update):
        msg.delete()


def get_message_type(msg: TGMessage):
    if msg.media_group_id:
        if save_media_group(msg.media_group_id):
            return 'album'
        return
    if any((e['type'] == 'url' for e in msg.entities)):
        return 'link'
    for field in MESSAGE_TYPES:
        if getattr(msg, field, None):
            return field


def get_chat_from_tg_chat(tg_chat: TGChat) -> Chat:
    if tg_chat.last_name:
        fallback_name = f'{tg_chat.first_name} {tg_chat.last_name}'
    else:
        fallback_name = tg_chat.first_name
    chat, _ = Chat.objects.update_or_create(
        id=tg_chat.id,
        defaults={
            'type': tg_chat.type,
            'username': tg_chat.username,
            'title': tg_chat.title or fallback_name,
        },
    )
    return chat


def get_user(update: Update):
    u: TGUser = update.effective_user
    user, _ = User.objects.update_or_create(
        id=u.id,
        defaults={
            'username': u.username,
            'first_name': u.first_name,
            'last_name': u.last_name,
        },
    )
    return user


def get_forward_from(msg: TGMessage):
    if msg.forward_from:
        u: TGUser = msg.forward_from
        forward, _ = User.objects.update_or_create(
            id=u.id,
            defaults={
                'username': u.username,
                'first_name': u.first_name,
                'last_name': u.last_name,
            },
        )
        return forward


def get_forward_from_chat(msg: TGMessage):
    if msg.forward_from_chat:
        return get_chat_from_tg_chat(msg.forward_from_chat)


def clear_buttons(buttons: list, emojis=False):
    buttons = [b for b in OrderedSet(buttons) if len(b) < 20]
    if emojis and not all([b in UNICODE_EMOJI for b in buttons]):
        return
    return buttons
