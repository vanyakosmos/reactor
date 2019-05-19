from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_reply_markup(rates: list):
    keys = []
    for rate in rates:
        text = rate['text']
        count = rate['count']
        payload = rate['text']
        if count:
            text = f'{text} {count}'
        keys.append(InlineKeyboardButton(text, callback_data=payload))

    keyboard = []
    max_cols = 4
    while keys:
        keyboard += [keys[:max_cols]]
        keys = keys[max_cols:]

    return InlineKeyboardMarkup(keyboard)
