from telegram import Update
from telegram.ext import CallbackContext

from core.models import Chat
from .consts import CHAT_FIELDS, MESSAGE_TYPES
from .utils import command, get_chat, clear_buttons


def change_buttons(update: Update, chat: Chat, values: list):
    if len(values) > 64:
        update.message.reply_text("Too many buttons.")
        return
    bs = clear_buttons(values)
    chat.buttons = bs
    chat.save()
    bs = ' '.join(bs)
    update.message.reply_text(f"New default buttons: [{bs}]")


def change_bool(update: Update, chat: Chat, values: list, field: str, true_text, false_text):
    option = values[0] if len(values) == 1 else None
    if option == 'true':
        setattr(chat, field, True)
        chat.save()
        reply = true_text
    elif option == 'false':
        setattr(chat, field, False)
        chat.save()
        reply = false_text
    else:
        reply = f"Unknown option '{option}'. Should be true or false."
    update.message.reply_text(reply)


def change_show_credits(update: Update, chat: Chat, values: list):
    change_bool(
        update,
        chat,
        values,
        field='show_credits',
        true_text="Will show message credits.",
        false_text="Will not show message credits.",
    )


def change_columns(update: Update, chat: Chat, values: list):
    if len(values) != 1 or not values[0].isdecimal():
        update.message.reply_text("Specify number of buttons per row (number of columns).")
        return
    option = int(values[0])
    min_col, max_col = 1, 6
    if not min_col <= option <= max_col:
        update.message.reply_text(f"Number of columns should be between {min_col} and {max_col}.")
        return
    chat.columns = option
    chat.save()
    update.message.reply_text(f"New number of buttons per row: {option}.")


def change_add_padding(update: Update, chat: Chat, values: list):
    change_bool(
        update,
        chat,
        values,
        field='add_padding',
        true_text="Will add padding to buttons.",
        false_text="Will not add padding to buttons.",
    )


def change_allowed_types(update: Update, chat: Chat, values: list):
    types = list(filter(lambda e: e in MESSAGE_TYPES, values))
    chat.allowed_types = types
    chat.save()
    types_str = ' '.join(sorted(types))
    update.effective_message.reply_text(f"Allowed types: [{types_str}].")


def change_allow_reactions(update: Update, chat: Chat, values: list):
    change_bool(
        update,
        chat,
        values,
        field='allow_reactions',
        true_text="Will add reactions on replies with +.",
        false_text="Will not add reactions on replies.",
    )


def change_force_emojis(update: Update, chat: Chat, values: list):
    change_bool(
        update,
        chat,
        values,
        field='force_emojis',
        true_text="Will allow only reactions with emojis.",
        false_text="Will allow any text as reaction.",
    )


def change_repost(update: Update, chat: Chat, values: list):
    change_bool(
        update,
        chat,
        values,
        field='repost',
        true_text="Will repost new messages.",
        false_text="Will reply to messages instead of reposting them.",
    )


@command('edit', pass_args=True, admin_required=True)
def command_edit(update: Update, context: CallbackContext):
    """
    Edit setting fields.
        ex: `/edit buttons a b c` - replace all buttons
        ex: `/edit buttons` - remove buttons
    """
    if len(context.args) < 2:
        return
    field, *values = context.args
    if field not in CHAT_FIELDS:
        return
    chat = get_chat(update)
    change_mapper = {
        'buttons': change_buttons,
        'show_credits': change_show_credits,
        'columns': change_columns,
        'add_padding': change_add_padding,
        'allowed_types': change_allowed_types,
        'allow_reactions': change_allow_reactions,
        'force_emojis': change_force_emojis,
        'repost': change_repost,
    }
    change_mapper[field](update, chat, values)
