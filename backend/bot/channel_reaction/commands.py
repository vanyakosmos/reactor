import logging

from telegram import Message as TGMessage, Update, User as TGUser
from telegram.ext import CallbackContext, Filters

from bot import redis, filters
from bot.redis import State
from bot.wrapper import command
from core.models import Message

logger = logging.getLogger(__name__)


@command('start', filters=Filters.private & filters.has_arguments, pass_args=True)
def command_start(update: Update, context: CallbackContext):
    """Initiate reaction."""
    user: TGUser = update.effective_user
    msg: TGMessage = update.effective_message

    message_id = context.args[0]
    try:
        Message.objects.get(id=message_id)
    except Message.DoesNotExist:
        logger.debug(f"Message {message_id} doesn't exist.")
        msg.reply_text(
            "Message you want to react to is invalid "
            "(either too old or magically disappeared from DB)."
        )
        return

    msg.reply_text('Now send me your reaction. It can be a single emoji or a sticker.')
    redis.set_state(user.id, State.reaction)
    redis.set_key(user.id, 'message_id', message_id)
