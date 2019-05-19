from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from core.models import Chat


def get_credits(update: Update):
    user = update.effective_user
    msg = update.effective_message
    data = {
        'from_name': user.full_name,
        'from_username': user.username,
    }
    if msg.forward_from:
        f = msg.forward_from
        data.update({
            'forward_name': f.full_name,
            'forward_username': f.username,
        })
    elif msg.forward_from_chat:
        f = msg.forward_from_chat
        data.update({
            'forward_chat_name': f.title,
            'forward_chat_username': f.username,
            'forward_chat_message_id': msg.forward_from_message_id,
        })
    return data


def make_credits_buttons(
    from_name=None,
    from_username=None,
    forward_name=None,
    forward_username=None,
    forward_chat_name=None,
    forward_chat_username=None,
    forward_chat_message_id=None,
):
    buttons = []

    # user
    if from_username:
        from_user_button = InlineKeyboardButton(
            f'by {from_name}',
            url=f'https://t.me/{from_username}',
        )
    else:
        from_user_button = InlineKeyboardButton(
            f"by {from_name}",
            callback_data='~',
        )
    buttons.append(from_user_button)

    # forward user
    if forward_name and from_username != forward_username:
        if forward_username:
            button = InlineKeyboardButton(
                text=f"from {forward_name}",
                url=f'https://t.me/{forward_username}',
            )
            buttons.append(button)
        else:
            from_user_button.text += f', from {forward_name}'

    # forward_chat
    if forward_chat_username:
        button = InlineKeyboardButton(
            text=f"from {forward_chat_name}",
            url=f'https://t.me/{forward_chat_username}/{forward_chat_message_id}',
        )
        buttons.append(button)

    return buttons


def make_reply_markup(
    update: Update,
    context: CallbackContext,
    rates: list,
    padding=False,
    max_cols=5,
    show_credits=False,
):
    keys = []
    for rate in rates:
        text = rate['text']
        count = rate['count']
        payload = rate['text']
        if count:
            text = f'{text} {count}'
        keys.append(InlineKeyboardButton(text, callback_data=payload))

    keyboard = []
    if show_credits:
        credits = get_credits(update)
        keyboard.append(make_credits_buttons(**credits))
    while keys:
        line = keys[:max_cols]
        if padding and len(line) != max_cols:
            line += [
                InlineKeyboardButton('+', url=f'https://t.me/{context.bot.username}')
                for _ in range(max_cols - len(line))
            ]
        keyboard += [line]
        keys = keys[max_cols:]

    return InlineKeyboardMarkup(keyboard)


def make_reply_markup_from_chat(update, context, reactions=None, chat=None):
    if not chat:
        chat, _ = Chat.objects.get_or_create(id=update.effective_message.chat_id)
    if not reactions:
        reactions = chat.reactions()
    reply_markup = make_reply_markup(
        update,
        context,
        reactions,
        show_credits=chat.show_credits,
        padding=chat.add_padding,
        max_cols=chat.columns,
    )
    return chat, reply_markup
