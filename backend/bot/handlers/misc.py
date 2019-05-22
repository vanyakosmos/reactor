import logging

from telegram import Update
from telegram.ext import CallbackContext, Filters

from core.models import Chat
from .utils import message_handler

logger = logging.getLogger(__name__)


def handle_error(update: Update, context: CallbackContext):
    logger.error(f"📑\n{update}")
    logger.exception(context.error)


@message_handler(Filters.status_update.new_chat_members)
def handle_new_member(update: Update, context: CallbackContext):
    msg = update.effective_message
    for member in msg.new_chat_members:
        if member.id == context.bot.id:
            Chat.objects.get_or_create(id=msg.chat_id)
