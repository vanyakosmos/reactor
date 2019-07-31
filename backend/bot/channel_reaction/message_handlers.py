import logging

from emoji import UNICODE_EMOJI
from telegram import (
    Update,
    User as TGUser,
)
from telegram.ext import CallbackContext, Filters

from bot import redis
from bot.filters import StateFilter
from bot.markup import make_reply_markup
from bot.wrapper import message_handler
from core.models import Message, Reaction

logger = logging.getLogger(__name__)


@message_handler(Filters.private & (Filters.text | Filters.sticker) & StateFilter.reaction)
def handle_reaction_response(update: Update, context: CallbackContext):
    """
    Respond to user's reaction after "start" commands.
    Update post's markup.
    """
    user: TGUser = update.effective_user
    msg = update.effective_message
    reaction = msg.text or (msg.sticker and msg.sticker.emoji)

    if reaction not in UNICODE_EMOJI:
        msg.reply_text(f"Reaction should be a single emoji.")
        return

    some_message_id = redis.get_key(user.id, 'message_id')
    try:
        message = Message.objects.prefetch_related().get(id=some_message_id)
    except Message.DoesNotExist:
        logger.debug(f"Message {some_message_id} doesn't exist.")
        msg.reply_text(f"Received invalid message ID from /start command.")
        return

    mids = message.ids
    _, button = Reaction.objects.react(
        user=user,
        button_text=reaction,
        **mids,
    )
    if not button:
        msg.reply_text(f"Post already has too many reactions.")
        return
    _, reply_markup = make_reply_markup(update, context.bot, message=message)
    context.bot.edit_message_reply_markup(reply_markup=reply_markup, **mids)
    msg.reply_text(f"Reacted with {reaction}")
