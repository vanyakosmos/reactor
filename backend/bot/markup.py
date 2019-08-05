from typing import Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot

from core.models import Chat, Message, Button

EMPTY_CB_DATA = '~'


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
            callback_data=EMPTY_CB_DATA,
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


def make_vote_keyboard(bot, inline_message_id, text="add reaction"):
    if not inline_message_id:
        return
    return InlineKeyboardMarkup.from_button(
        InlineKeyboardButton(
            text=text,
            url=f'https://t.me/{bot.username}?start={inline_message_id}',
        )
    )


def merge_keyboards(*keyboards: Optional[InlineKeyboardMarkup]):
    """Merge keyboards by columns."""
    ks = []
    for keyboard in keyboards:
        if keyboard:
            ks.extend(keyboard.inline_keyboard)
    if not ks:
        return
    ks = ks[:10]  # telegram limit is 10x10
    return InlineKeyboardMarkup(ks)


def flatten_list(ls: list):
    res = []
    for item in ls:
        if isinstance(item, list):
            res.extend(flatten_list(item))
        else:
            res.append(item)
    return res


def fluid_merge_keyboards(*keyboards: Optional[InlineKeyboardMarkup], max_cols: int, padding=False):
    """Merge keyboards button by button."""
    buttons = flatten_list([kb.inline_keyboard for kb in keyboards if kb])
    buttons = list(filter(lambda b: b.callback_data != EMPTY_CB_DATA, buttons))

    if padding:
        extend_with_padding(buttons, max_cols)

    if not buttons:
        return
    ks = split_to_columns(buttons, max_cols)
    ks = ks[:10]  # telegram limit is 10x10
    return InlineKeyboardMarkup(ks)


def gen_buttons(rates: list, blank=False, sort=False):
    for i, rate in enumerate(rates):
        if isinstance(rate, str):
            rates[i] = (rate, 0)

    if sort:
        rates.sort(key=lambda e: -e[1])

    result = []
    for text, count in rates:
        payload = EMPTY_CB_DATA if blank else f"button:{text}"
        count_text = str(count)
        if count > 1000:
            if count % 1000 >= 100:
                count_text = f'{count / 1000:.1f}k'
            else:
                count_text = f'{count // 1000}k'
        if count > 0:
            text = f'{text} {count_text}'
        result.append(InlineKeyboardButton(text, callback_data=payload))
    return result


def split_to_columns(lines: list, max_cols: int):
    res = []
    while lines:
        line = lines[:max_cols]
        res.append(line)
        lines = lines[max_cols:]
    return res


def extend_with_padding(buttons: list, max_cols: int):
    if len(buttons) > max_cols:
        n = max_cols - len(buttons) % max_cols
        buttons.extend([InlineKeyboardButton('.', callback_data=EMPTY_CB_DATA)] * n)


def make_reactions_keyboard(rates: list, padding=False, max_cols=5, blank=False, sort=False):
    buttons = gen_buttons(rates, blank, sort)

    if padding:
        extend_with_padding(buttons, max_cols)

    keyboard = split_to_columns(buttons, max_cols)
    return InlineKeyboardMarkup(keyboard)


def make_reply_markup(
    update: Update,
    bot: Bot,
    reactions: list = None,
    chat: Chat = None,
    message: Message = None,
    anonymous=False,
) -> Tuple[Optional[Chat], InlineKeyboardMarkup]:
    if not chat:
        if message:
            chat = message.chat
        else:
            chat, _ = Chat.objects.get_or_create(id=update.effective_message.chat_id)
    if reactions is None:
        if message:
            reactions = Button.objects.reactions(**message.ids)
        elif chat:
            reactions = chat.buttons
        else:
            raise ValueError("can't determine reactions")

    # message doesn't have chat and it wasn't provided as arg
    # which means that we are creating keyboard for inline post
    if not chat:
        max_cols = 5
        vote_keyboard = make_vote_keyboard(bot, message and message.inline_message_id, text='add')
        reactions_keyboard = make_reactions_keyboard(reactions, max_cols=max_cols)
        reply_markup = fluid_merge_keyboards(
            reactions_keyboard,
            vote_keyboard,
            max_cols=max_cols,
            padding=True,
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
        credits = {}

    vote_keyboard = make_vote_keyboard(bot, message and message.inline_message_id, text='add')
    credits_keyboard = make_credits_keyboard(**credits)
    reactions_keyboard = make_reactions_keyboard(
        reactions,
        padding=chat.add_padding,
        max_cols=chat.columns,
    )
    reactions_keyboard = fluid_merge_keyboards(
        reactions_keyboard,
        vote_keyboard,
        padding=chat.add_padding,
        max_cols=chat.columns,
    )
    reply_markup = merge_keyboards(credits_keyboard, reactions_keyboard)
    return chat, reply_markup
