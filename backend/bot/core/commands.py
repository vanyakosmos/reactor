import logging

from django.conf import settings
from telegram import Update
from telegram.ext import CallbackContext, Filters

from bot import filters
from .edit_command import command_edit
from .utils import normalize_text, get_commands_help
from bot.channel_publishing.commands import command_create
from bot.stats import command_reactions, command_champions
from bot.wrapper import command
from core.models import Chat

logger = logging.getLogger(__name__)


@command(('help', 'h'))
def command_help(update: Update, _: CallbackContext):
    """Show list of commands."""
    text = '\n'.join([
        "This bot can automagically add reactions panel to messages in group chats "
        "or create reactable messages for channels.",
        '',
        *get_commands_help(command_help, command_guide, command_donate),
        '',
        "*Private chat commands:*",
        *get_commands_help(command_create),
        '',
        "*Group commands:*",
        *get_commands_help(command_settings, command_edit, command_reactions, command_champions),
    ])
    update.message.reply_markdown(text)


def format_chat_settings(chat: Chat, show_help_text=False):
    settings_list = []
    just = max(map(len, settings.CHAT_FIELDS))
    for field, help_text in settings.CHAT_FIELDS.items():
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
    text = '\n'.join(settings_list)
    text = f"```\n{text}\n```"
    if not show_help_text:
        text = f"Use `/settings help` for more details.\n{text}"
    return text


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
    update.message.reply_markdown(content)


@command(('settings', 'sets'), filters=Filters.private)
def command_settings_private(update: Update, _: CallbackContext):
    update.message.reply_text("Can show settings only for group chat.")


@command('start', filters=(Filters.private | Filters.group) & ~filters.has_arguments)
def command_start(update: Update, context: CallbackContext):
    command_help(update, context)


@command('guide', filters=Filters.private | Filters.group)
def command_guide(update: Update, _: CallbackContext):
    """Show how to use the bot."""
    text = f"""
    *Usage in group chat:*
    
    - add bot to the chat
    - pick mode:
        - reply to original message with reactions keyboard
            - setup: `/edit repost 0`
        - (default) repost message: delete original message, repost message with same content on bot's behalf while showing credits of original poster.
            - bot must be admin with "delete message" permission
            - setup: `/edit repost 1`
    - using `/settings` and `/edit` configure bot for your chat
        - change default buttons
        - credits visibility
        - type of messages to be reposted automatically. default: photo, video, animation, links, forwards

    *Adding custom reaction in group:*
    
    - reply to bot's message with *+text*
    - *+* is required
    - *text* is your new reaction, can be any text up to {settings.MAX_BUTTON_LEN}
    
    *Posting into channel:*
    
    - go to the private chat with bot
    - type `/create`
    - send message to publish
    - choose buttons
    - publish message to another chat/channel
    
    *Adding custom reaction to posts created via inline and* `/create`
    
    - click "add reaction"
    - tg will redirect to chat with bot
    - click "start"
    - send reaction (emoji only)
    """
    text = normalize_text(text)
    if settings.GITHUB_URL:
        text = f"{text}\n\nMore details [here]({settings.GITHUB_URL}/blob/master/README.md)"
    update.message.reply_markdown(text, disable_web_page_preview=True)


@command('donate', filters=Filters.private | Filters.group)
def command_donate(update: Update, _: CallbackContext):
    """Show project's support options."""
    if not all([settings.GITHUB_URL, settings.CREDIT_CARD, settings.PATREON_URL]):
        update.message.reply_markdown("not yet")
        return
    text = f"""
    Support the project by:
    - donating pull requests or stars: [github]({settings.GITHUB_URL})
    - giving me real money: {settings.CREDIT_CARD}
    - donating every month (lol): [patreon]({settings.PATREON_URL})
    """
    text = normalize_text(text)
    update.message.reply_markdown(text, disable_web_page_preview=True)
