import regex
from telegram import Message as TGMessage

from bot.utils import clear_buttons

MAGIC_MARK = regex.compile(r'^\.(-|\+|~|`.*`)+.*$')


def get_magic_marks(text: str):
    if not text:
        return
    m = MAGIC_MARK.match(text)
    if m:
        return m.captures(1)


def get_magic_marks_from_msg(msg: TGMessage):
    text: str = msg.text or msg.caption
    return get_magic_marks(text)


def remove_magic_marks(msg: TGMessage, marks: list):
    """Return False if text was removed and message can't be reposted."""
    had_text = bool(msg.text)
    text = msg.text or msg.caption
    text = text[1:]  # remove .
    s = sum(map(len, marks))
    if len(text) > s:
        text = text[s:]
    else:
        text = None
    msg.text = text
    msg.caption = text
    return not (had_text and text is None)


def process_magic_mark(msg: TGMessage):
    force = 0
    anon = False
    skip = False
    buttons = None
    marks = get_magic_marks_from_msg(msg)
    if not marks:
        return force, anon, skip, buttons
    if not remove_magic_marks(msg, marks):
        skip = True
    if '-' in marks:
        skip = True
    force = marks.count('+')
    if '~' in marks:
        anon = True
    for mark in marks:
        if '`' in mark:
            buttons = mark[1:-1].split()
            buttons = clear_buttons(buttons)
            break
    return force, anon, skip, buttons
