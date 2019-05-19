from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot


def get_reply_markup(bot: Bot, rates: list, padding=False, max_cols=5):
    keys = []
    for rate in rates:
        text = rate['text']
        count = rate['count']
        payload = rate['text']
        if count:
            text = f'{text} {count}'
        keys.append(InlineKeyboardButton(text, callback_data=payload))

    keyboard = []
    while keys:
        line = keys[:max_cols]
        if padding and len(line) != max_cols:
            line += [
                InlineKeyboardButton('+', url=f'https://t.me/{bot.username}')
                for _ in range(max_cols - len(line))
            ]
        keyboard += [line]
        keys = keys[max_cols:]

    return InlineKeyboardMarkup(keyboard)
