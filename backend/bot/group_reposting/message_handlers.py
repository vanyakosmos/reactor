import logging

from django.utils import timezone
from telegram import (Message as TGMessage, Update)
from telegram.ext import CallbackContext, Filters

from bot.magic_marks import process_magic_mark
from bot.markup import make_reply_markup
from bot.utils import (
    get_forward_from,
    get_forward_from_chat,
    get_message_type,
    repost_message,
    try_delete,
)
from bot.wrapper import message_handler
from core.models import Chat, Message, User

logger = logging.getLogger(__name__)


def process_message(
    update: Update,
    context: CallbackContext,
    msg_type: str,
    chat: Chat,
    anonymous: bool,
    buttons=None,
    repost=False,
):
    msg: TGMessage = update.effective_message
    bot = context.bot

    chat, reply_markup = make_reply_markup(update, bot, buttons, chat=chat, anonymous=anonymous)

    should_repost = (chat.repost or repost) and msg_type != 'album'

    if should_repost:
        sent_msg = repost_message(msg, bot, msg_type, reply_markup)
    else:
        sent_msg = msg.reply_text(
            text='^',
            disable_notification=True,
            reply_markup=reply_markup,
        )

    logger.debug(f"sent_msg: {sent_msg}")
    if sent_msg:
        if should_repost:
            try_delete(bot, update, msg)
        Message.objects.create_from_tg_ids(
            sent_msg.chat_id,
            sent_msg.message_id,
            date=timezone.make_aware(msg.date),
            buttons=buttons,
            anonymous=anonymous,
            original_message_id=msg.message_id,
            from_user=User.objects.from_update(update),
            forward_from=get_forward_from(msg),
            forward_from_chat=get_forward_from_chat(msg),
            forward_from_message_id=msg.forward_from_message_id,
        )


@message_handler(Filters.group & ~Filters.reply & ~Filters.status_update)
def handle_message(update: Update, context: CallbackContext):
    msg: TGMessage = update.effective_message

    force, anonymous, skip, buttons = process_magic_mark(msg)
    logger.debug(f"force: {force}, anonymous: {anonymous}, skip: {skip}, buttons: {buttons}")
    if skip:
        logger.debug('skipping message processing')
        return

    chat = Chat.objects.from_update(update)
    allowed_types = chat.allowed_types
    allow_forward = 'forward' in allowed_types

    msg_type = get_message_type(msg)
    forward = bool(msg.forward_date)
    logger.debug(f"msg_type: {msg_type}, forward: {forward}")

    if force > 0 or msg_type in allowed_types or forward and allow_forward:
        process_message(update, context, msg_type, chat, anonymous, buttons, repost=force > 1)
