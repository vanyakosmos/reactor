import logging

from telegram import Update
from telegram.ext import CallbackContext

from core.models import Button, Reaction
from .markup import get_reply_markup

logger = logging.getLogger(__name__)


def reply_to_reaction(bot, query, button, reaction):
    if reaction:
        reply = f"You reacted {button.text}"
    else:
        reply = "You removed reaction"
    bot.answer_callback_query(query.id, reply)


def handle_button_callback(update: Update, context: CallbackContext):
    msg = update.effective_message
    user = update.effective_user
    query = update.callback_query

    reaction, button = Reaction.objects.react(
        user_id=user.id,
        chat_id=msg.chat_id,
        message_id=msg.message_id,
        button_text=query.data,
    )
    reply_to_reaction(context.bot, query, button, reaction)
    reactions = Button.objects.reactions(msg.chat_id, msg.message_id)
    reply_markup = get_reply_markup(context.bot, reactions)
    msg.edit_reply_markup(reply_markup=reply_markup)
