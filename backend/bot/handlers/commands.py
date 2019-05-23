import logging

from telegram import Message as TGMessage, ParseMode, Update, User as TGUser
from telegram.ext import CallbackContext, Filters

from bot import redis
from core.models import Chat
# noinspection PyUnresolvedReferences
from .edit_command import command_edit
from .consts import CHAT_FIELDS
from .utils import command, get_chat

logger = logging.getLogger(__name__)


@command('help')
def command_help(update: Update, context: CallbackContext):
    text = '\n'.join([
        "This bot can automagically add reactions panel to messages.\n",
        "/help - print commands",
        "Private chat commands:",
        "/create - create new post",
        "Chat commands:",
        "/settings - show chat settings",
        "  ex: `/settings help` - show commands and help text",
        "/edit - change setting fields",
        "  ex: `/edit buttons a b c` - replace all buttons",
        "  ex: `/edit buttons` - remove buttons",
        "/patch - add/remove items to/from list-like setting's fields.",
        "  ex: `/patch + buttons d g` - add 2 new buttons",
        "  ex: `/patch - buttons a` - remove 1 button if present",
    ])
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def format_chat_settings(chat: Chat, show_help_text=False):
    settings_list = []
    for field, help_text in CHAT_FIELDS.items():
        value = getattr(chat, field)
        if isinstance(value, list):
            value = f"[{' '.join(value)}]"
        elif isinstance(value, bool):
            value = 'true' if value else 'false'
        if show_help_text:
            settings_list.append(f"# {help_text}\n{field} = {value}\n")
        else:
            field = field.ljust(15)
            settings_list.append(f"{field} - {value}")
    settings_text = '\n'.join(settings_list)
    return f"```\n{settings_text}\n```"


@command('settings', pass_args=True)
def command_settings(update: Update, context: CallbackContext):
    """
    Show list of settings.
    """
    show_help_text = context.args and context.args[0] == 'help'
    chat = get_chat(update)
    content = format_chat_settings(chat, show_help_text)
    update.message.reply_text(content, parse_mode=ParseMode.MARKDOWN)


@command('start', pass_args=True, filters=Filters.private)
def command_start(update: Update, context: CallbackContext):
    if not context.args:
        return
    user: TGUser = update.effective_user
    msg: TGMessage = update.effective_message
    msg.reply_text('Now send me your reaction.')
    redis.await_reaction(user.id, context.args[0])


@command('create', filters=Filters.private)
def command_create(update: Update, context: CallbackContext):
    user: TGUser = update.effective_user
    msg: TGMessage = update.effective_message
    msg.reply_text('Now send me your message to which you want me to add reactions panel.')
    redis.await_create(user.id)
