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


def make_credits_keyboard(
    from_name=None,
    from_username=None,
    forward_name=None,
    forward_username=None,
    forward_chat_name=None,
    forward_chat_username=None,
    forward_chat_message_id=None,
):
    if not from_name:
        return

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

    return InlineKeyboardMarkup.from_row(buttons)


def make_vote_keyboard(bot, inline_message_id):
    if not inline_message_id:
        return
    return InlineKeyboardMarkup.from_button(
        InlineKeyboardButton(
            text="add reaction",
            url=f'https://t.me/{bot.username}?start={inline_message_id}',
        )
    )


def merge_keyboards(*keyboards: InlineKeyboardMarkup):
    """Merge keyboards by columns."""
    ks = []
    for keyboard in keyboards:
        if keyboard:
            ks.extend(keyboard.inline_keyboard)
    return InlineKeyboardMarkup(ks)


def gen_buttons(rates: list, blank: bool, sort=False):
    for i, rate in enumerate(rates):
        if isinstance(rate, str):
            rates[i] = (rate, 0)

    if sort:
        rates.sort(key=lambda e: -e[1])

    result = []
    for text, count in rates:
        payload = '~' if blank else f"button:{text}"
        if count > 1000:
            count /= 1000
            count = f'{count:.1f}k'
        if count > 0:
            text = f'{text} {count}'
        result.append(InlineKeyboardButton(text, callback_data=payload))
    return result


def make_reactions_keyboard(rates: list, padding=False, max_cols=5, blank=False, sort=False):
    keys = gen_buttons(rates, blank, sort)

    keyboard = []
    while keys:
        line = keys[:max_cols]
        if padding and len(line) != max_cols and len(keyboard) >= 1:
            line += [
                InlineKeyboardButton('.', callback_data='~')
                for _ in range(max_cols - len(line))
            ]
        keyboard.append(line)
        keys = keys[max_cols:]
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
        reactions = chat.buttons

    # message doesn't have chat and it wasn't provided as arg
    # which means that we are creating keyboard for inline post
    if not chat:
        vote_keyboard = make_vote_keyboard(context.bot, message and message.inline_message_id)
        reactions_keyboard = make_reactions_keyboard(reactions)
        reply_markup = merge_keyboards(vote_keyboard, reactions_keyboard)
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

    vote_keyboard = make_vote_keyboard(context.bot, message and message.inline_message_id)
    credits_keyboard = make_credits_keyboard(**(credits or {}))
    reactions_keyboard = make_reactions_keyboard(reactions, chat.add_padding, chat.columns)
    reply_markup = merge_keyboards(vote_keyboard, credits_keyboard, reactions_keyboard)
    return chat, reply_markup
