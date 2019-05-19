import logging

from django.utils.datastructures import OrderedSet
from telegram import ParseMode, Update
from telegram.ext import CallbackContext

from .utils import command, get_chat

logger = logging.getLogger(__name__)


@command('help')
def command_help(update: Update, context: CallbackContext):
    text = '\n'.join([
        "This bot will automagically add reactions panel to your images/gifs/videos/links.",
        "`/help` - print this message",
        "`/set <button> [<button>...]` - set up buttons",
        "`/get` - get list of default buttons for this chat",
    ])
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@command('get')
def command_get_buttons(update: Update, context: CallbackContext):
    chat = get_chat(update)
    bs = ', '.join(chat.buttons)
    update.message.reply_text(f"Current default buttons: [{bs}]")


@command('set', pass_args=True)
def command_set_buttons(update: Update, context: CallbackContext):
    chat = get_chat(update)
    if len(context.args) > 80:
        update.message.reply_text("Number of buttons is too big.")
        return
    bs = [b for b in OrderedSet(context.args) if len(b) < 20]
    chat.buttons = bs
    chat.save()
    bs = ', '.join(bs)
    update.message.reply_text(f"New default buttons: [{bs}]")
