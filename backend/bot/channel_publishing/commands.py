import logging

from telegram import Message as TGMessage, Update, User as TGUser
from telegram.ext import CallbackContext, Filters

from bot import redis
from bot.redis import State
from bot.wrapper import command
from core.models import User

logger = logging.getLogger(__name__)


@command('create', filters=Filters.private)
def command_create(update: Update, _: CallbackContext):
    """Trigger creation of the new post."""
    user: TGUser = update.effective_user
    msg: TGMessage = update.effective_message
    User.objects.from_tg_user(user)  # create user before using it in MessageToPublish
    msg.reply_text('Send message to which you want me to add reactions.')
    redis.set_state(user.id, State.create_start)
