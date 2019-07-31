import logging

from telegram import ParseMode, Update
from telegram.ext import CallbackContext, Filters

from bot.channel_publishing.commands import command_create
from bot.consts import CHAT_FIELDS
from bot.wrapper import command
from core.models import Chat
from .edit_command import command_edit

logger = logging.getLogger(__name__)


def get_commands_help(*commands):
    for cmd in commands:
        names = ' '.join([f"/{c}" for c in cmd.handler.command])
        docs = cmd.__doc__
        if docs:
            docs = docs.strip()
            yield f"{names} - {docs}"
        else:
            yield names


@command(('help', 'h'))
def command_help(update: Update, context: CallbackContext):
    """Show list of commands."""
    text = '\n'.join([
        "This bot can automagically add reactions panel to messages.\n",
        *get_commands_help(command_help),
        "Private chat commands:",
        *get_commands_help(command_create),
        "Chat commands:",
        *get_commands_help(command_settings, command_edit),
    ])
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def format_chat_settings(chat: Chat, show_help_text=False):
    settings_list = []
    just = max(map(len, CHAT_FIELDS))
    for field, help_text in CHAT_FIELDS.items():
        value = getattr(chat, field)
        if isinstance(value, list):
            value = f"[{' '.join(value)}]"
        elif isinstance(value, bool):
            value = 'true' if value else 'false'
        if show_help_text:
            settings_list.append(f"# {help_text}\n> {field} = {value}\n")
        else:
            field = field.ljust(just)
            settings_list.append(f"{field} - {value}")
    settings_text = '\n'.join(settings_list)
    return f"```\n{settings_text}\n```"


@command(('settings', 'sets'), filters=Filters.group, pass_args=True)
def command_settings(update: Update, context: CallbackContext):
    """
    Show list of group chat settings.
        ex: `/settings` - show commands
        ex: `/settings help` - show commands and help text
    """
    show_help_text = context.args and context.args[0] == 'help'
    chat = Chat.objects.from_update(update)
    content = format_chat_settings(chat, show_help_text)
    update.message.reply_text(content, parse_mode=ParseMode.MARKDOWN)


@command(('settings', 'sets'), filters=Filters.private)
def command_settings_private(update: Update, _: CallbackContext):
    update.message.reply_text("Can show settings only in group chat.")
