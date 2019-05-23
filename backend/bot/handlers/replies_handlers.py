import logging

from telegram import Update
from telegram.ext import CallbackContext, Filters

from core.models import Button, Reaction, Message
from .markup import make_reply_markup_from_chat
from .utils import message_handler, try_delete
from emoji import UNICODE_EMOJI

logger = logging.getLogger(__name__)


@message_handler(Filters.reply & Filters.text & Filters.regex(r'\+(.+)'))
def handle_reaction_reply(update: Update, context: CallbackContext):
    user = update.effective_user
    msg = update.effective_message
    reaction = context.match[1]
    reply = msg.reply_to_message

    try:
        message = Message.objects.prefetch_related().get_by_ids(reply.chat_id, reply.message_id)
    except Message.DoesNotExist:
        logger.debug(f"message doesn't exist. reply: {reply}")
        return

    if not message.chat.allow_reactions:
        logger.debug("reactions are not allowed")
        return

    if message.chat.force_emojis and reaction not in UNICODE_EMOJI:
        logger.debug("can't react with non-emoji text")
        return

    Reaction.objects.react(
        user=user,
        chat_id=reply.chat_id,
        message_id=reply.message_id,
        inline_message_id=None,
        button_text=reaction,
    )
    reactions = Button.objects.reactions(reply.chat_id, reply.message_id)
    _, reply_markup = make_reply_markup_from_chat(update, context, reactions, message=message)
    reply.edit_reply_markup(reply_markup=reply_markup)
    try_delete(context.bot, update, msg)
