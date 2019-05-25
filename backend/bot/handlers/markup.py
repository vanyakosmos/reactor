from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

from core.models import Chat, Message


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


def get_credits_from_message(message: Message):
    data = {
        'from_name': message.from_user.tg.full_name,
        'from_username': message.from_user.username,
    }
    ff = message.forward_from
    if ff:
        data.update({
            'forward_name': ff.tg.full_name,
            'forward_username': ff.username,
        })
    ffc = message.forward_from_chat
    if ffc:
        data.update({
            'forward_chat_name': ffc.title,
            'forward_chat_username': ffc.username,
            'forward_chat_message_id': message.forward_from_message_id,
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


def make_vote_button(bot, inline_message_id):
    return InlineKeyboardButton(
        text="vote",
        url=f'https://t.me/{bot.username}?start={inline_message_id}',
    )


def make_reply_markup(
    bot,
    rates: list,
    padding=False,
    max_cols=5,
    credits=None,
    vote_payload=None,
    blank=False,
):
    keys = []
    for rate in rates:
        text = rate['text']
        count = rate['count']
        payload = '~' if blank else f"button:{text}"
        if count:
            text = f'{text} {count}'
        keys.append(InlineKeyboardButton(text, callback_data=payload))

    keyboard = []
    if vote_payload:
        keyboard.append([make_vote_button(bot, vote_payload)])
    if credits:
        keyboard.append(make_credits_buttons(**credits))
    buttons = []
    while keys:
        line = keys[:max_cols]
        if padding and len(line) != max_cols and len(buttons) >= 1:
            line += [
                InlineKeyboardButton('.', callback_data='~')
                for _ in range(max_cols - len(line))
            ]
        buttons.append(line)
        keys = keys[max_cols:]
    keyboard.extend(buttons)
    return InlineKeyboardMarkup(keyboard)


def make_reply_markup_from_chat(
    update,
    context,
    reactions=None,
    chat=None,
    message=None,
    anonymous=False,
):
    if not chat:
        if message:
            chat = message.chat
        else:
            chat, _ = Chat.objects.get_or_create(id=update.effective_message.chat_id)
    if reactions is None:
        reactions = chat.reactions()

    # message doesn't have chat and it wasn't provided as arg
    if not chat:
        reply_markup = make_reply_markup(
            context.bot,
            reactions,
            vote_payload=message and message.inline_message_id,
        )
        return None, reply_markup

    if (
        chat.show_credits and chat.repost and not anonymous and
        (not message or not message.anonymous)
    ):
        if message:
            credits = get_credits_from_message(message)
        else:
            credits = get_credits(update)
    else:
        credits = None
    reply_markup = make_reply_markup(
        context.bot,
        reactions,
        credits=credits,
        padding=chat.add_padding,
        max_cols=chat.columns,
        vote_payload=message and message.inline_message_id,
    )
    return chat, reply_markup
