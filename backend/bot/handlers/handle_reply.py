import logging
import re

from telegram import Update
from telegram.ext import CallbackContext, Filters

from core.models import Button, Message as MessageModel, Reaction
from .markup import make_reply_markup_from_chat
from .utils import message_handler, try_delete

logger = logging.getLogger(__name__)


@message_handler(Filters.reply & Filters.text)
def handle_reply(update: Update, context: CallbackContext):
    user = update.effective_user
    msg = update.effective_message
    match = re.match(r'\+(\w+)', msg.text)
    if not match:
        return
    reaction = match[1]
    try_delete(context.bot, update, msg)

    reply = msg.reply_to_message
    umid = MessageModel.get_id(reply.chat_id, reply.message_id)
    try:
        Button.objects.get(message_id=umid, text=reaction)
    except Button.DoesNotExist:
        b = Button.objects.filter_by_message(reply.chat_id, reply.message_id).last()
        index = b.index + 1 if b else 0
        Button.objects.create(message_id=umid, text=reaction, index=index)

    Reaction.objects.react(
        user_id=user.id,
        chat_id=reply.chat_id,
        message_id=reply.message_id,
        button_text=reaction,
    )
    reactions = Button.objects.reactions(reply.chat_id, reply.message_id)
    _, reply_markup = make_reply_markup_from_chat(update, context, reactions)
    reply.edit_reply_markup(reply_markup=reply_markup)
