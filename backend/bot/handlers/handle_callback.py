import logging

from telegram import Update
from telegram.ext import CallbackContext, run_async

from core.models import Button, Reaction, Message
from .markup import make_reply_markup_from_chat

logger = logging.getLogger(__name__)


def reply_to_reaction(bot, query, button, reaction):
    if reaction:
        reply = f"You reacted {button.text}"
    else:
        reply = "You removed reaction"
    bot.answer_callback_query(query.id, reply)


@run_async
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
    message = Message.objects.prefetch_related().get_by_ids(msg.chat_id, msg.message_id)
    _, reply_markup = make_reply_markup_from_chat(update, context, reactions, message=message)
    msg.edit_reply_markup(reply_markup=reply_markup)
