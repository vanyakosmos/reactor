import logging

from telegram import Update
from telegram.ext import CallbackContext, Filters

from core.models import Button, Reaction, Message
from .markup import make_reply_markup_from_chat
from .utils import message_handler, try_delete

logger = logging.getLogger(__name__)


@message_handler(Filters.reply & Filters.text & Filters.regex(r'\+(.+)'))
def handle_reaction_reply(update: Update, context: CallbackContext):
    user = update.effective_user
    msg = update.effective_message
    reaction = context.match[1]
    try_delete(context.bot, update, msg)

    reply = msg.reply_to_message

    try:
        message = Message.objects.prefetch_related().get_by_ids(reply.chat_id, reply.message_id)
    except Message.DoesNotExist:
        logger.debug(f"Message doesn't exist.")
        return

    Button.objects.create_for_reaction(reaction, reply.chat_id, reply.message_id)
    Reaction.objects.react(
        user_id=user.id,
        chat_id=reply.chat_id,
        message_id=reply.message_id,
        button_text=reaction,
    )
    reactions = Button.objects.reactions(reply.chat_id, reply.message_id)
    _, reply_markup = make_reply_markup_from_chat(update, context, reactions, message=message)
    reply.edit_reply_markup(reply_markup=reply_markup)
