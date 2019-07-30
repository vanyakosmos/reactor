import logging

from telegram import Message as TGMessage, Update, User as TGUser
from telegram.ext import CallbackContext, Filters

from bot import redis
from bot.redis import State
from bot.wrapper import command

logger = logging.getLogger(__name__)


@command('create', filters=Filters.private)
def command_create(update: Update, _: CallbackContext):
    """
    Trigger creation of the new post.
    Change user's dialog state.
    """
    user: TGUser = update.effective_user
    msg: TGMessage = update.effective_message
    msg.reply_text('Send message to which you want me to add reactions.')
    redis.set_state(user.id, State.create_start)
