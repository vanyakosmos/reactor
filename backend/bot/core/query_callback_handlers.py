import logging

from telegram import Update
from telegram.error import BadRequest, TimedOut
from telegram.ext import CallbackContext, run_async

from core.models import Reaction, Message
from bot.markup import make_reply_markup
from bot.wrapper import callback_query_handler

logger = logging.getLogger(__name__)


def reply_to_reaction(bot, query, button, reaction):
    if reaction:
        reply = f"You reacted with {button.text}."
    else:
        reply = "You took your reaction back."
    bot.answer_callback_query(query.id, reply)


@callback_query_handler(pattern=r"^button:(.+)$")
@run_async
def handle_button_callback(update: Update, context: CallbackContext):
    msg = update.effective_message
    user = update.effective_user
    query = update.callback_query
    text = context.match[1]

    mids = dict(
        chat_id=msg and msg.chat_id,
        message_id=msg and msg.message_id,
        inline_message_id=query.inline_message_id,
    )
    try:
        message = Message.objects.prefetch_related().get_by_ids(**mids)
    except Message.DoesNotExist:
        logger.debug(f"Message {mids} doesn't exist.")
        return

    reaction, button = Reaction.objects.react(
        user=user,
        button_text=text,
        **mids,
    )
    reply_to_reaction(context.bot, query, button, reaction)
    _, reply_markup = make_reply_markup(update, context.bot, message=message)
    try:
        context.bot.edit_message_reply_markup(reply_markup=reply_markup, **mids)
    except TimedOut:
        logger.debug("timeout")
    except BadRequest as e:
        logger.debug(f"😡 {e}")


@callback_query_handler(pattern="^~$")
@run_async
def handle_empty_callback(update: Update, _: CallbackContext):
    update.callback_query.answer(cache_time=10)
