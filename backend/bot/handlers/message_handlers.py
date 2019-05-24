import logging
import regex

from django.utils import timezone
from emoji import UNICODE_EMOJI
from telegram import (
    Update,
    Message as TGMessage,
    User as TGUser,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import CallbackContext, Filters

from bot import redis
from bot.redis import State
from core.models import Button, Chat, Message, Reaction
from .filters import StateFilter
from .markup import make_reply_markup_from_chat
from .utils import (
    message_handler,
    try_delete,
    get_message_type,
    get_chat_from_tg_chat,
    get_forward_from,
    get_user,
    get_forward_from_chat,
    clear_buttons,
    get_reactions,
)

logger = logging.getLogger(__name__)
MAGIC_MARK = regex.compile(r'\.(-|\+|~|`.*`)+.*')


def process_message(
    update: Update,
    context: CallbackContext,
    msg_type: str,
    chat: Chat,
    anonymous: bool,
    buttons=None,
    repost=False,
):
    msg: TGMessage = update.effective_message
    bot = context.bot

    reactions = get_reactions(buttons) if buttons is not None else None
    chat, reply_markup = make_reply_markup_from_chat(
        update,
        context,
        reactions,
        chat=chat,
        anonymous=anonymous,
    )

    repost_message = (chat.repost or repost) and msg_type != 'album'

    if repost_message:
        config = {
            'chat_id': msg.chat_id,
            'text': msg.text_html,
            'caption': msg.caption_html,
            'disable_notification': True,
            'parse_mode': 'HTML',
            'reply_markup': reply_markup,
            # files
            'photo': msg.photo and msg.photo[0].file_id,
            'video': msg.video and msg.video.file_id,
            'animation': msg.animation and msg.animation.file_id,
            'document': msg.document and msg.document.file_id,
            'audio': msg.audio and msg.audio.file_id,
            'voice': msg.voice and msg.voice.file_id,
            'video_note': msg.video_note and msg.video_note.file_id,
            'sticker': msg.sticker and msg.sticker.file_id,
        }
        sender_map = {
            'text': bot.send_message,
            'link': bot.send_message,
            'photo': bot.send_photo,
            'video': bot.send_video,
            'animation': bot.send_animation,
            'document': bot.send_document,
            'audio': bot.send_audio,
            'voice': bot.send_voice,
            'video_note': bot.send_video_note,
            'sticker': bot.send_sticker,
        }
        if msg_type in sender_map:
            sent_msg = sender_map[msg_type](**config)
        else:
            sent_msg = None
    else:
        sent_msg = msg.reply_text(
            text='^',
            disable_notification=True,
            reply_markup=reply_markup,
        )

    logger.debug(f"sent_msg: {sent_msg}")
    if sent_msg:
        if repost_message:
            try_delete(bot, update, msg)
        Message.objects.create_from_tg_ids(
            sent_msg.chat_id,
            sent_msg.message_id,
            buttons=buttons,
            anonymous=anonymous,
            date=timezone.make_aware(msg.date),
            original_message_id=msg.message_id,
            from_user=get_user(update),
            forward_from=get_forward_from(msg),
            forward_from_chat=get_forward_from_chat(msg),
            forward_from_message_id=msg.forward_from_message_id,
        )


def get_magic_marks(msg: TGMessage):
    text: str = msg.text or msg.caption
    if not text:
        return
    m = MAGIC_MARK.match(text)
    if m:
        return m.captures(1)


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
    marks = get_magic_marks(msg)
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
            break
    return force, anon, skip, buttons


@message_handler(Filters.group & ~Filters.reply & ~Filters.status_update)
def handle_message(update: Update, context: CallbackContext):
    msg: TGMessage = update.effective_message

    force, anonymous, skip, buttons = process_magic_mark(msg)
    if buttons:
        buttons = clear_buttons(buttons)
    logger.debug(f"force: {force}, anonymous: {anonymous}, skip: {skip}, buttons: {buttons}")
    if skip:
        logger.debug('skipping message processing')
        return

    chat = get_chat_from_tg_chat(update.effective_chat)
    allowed_types = chat.allowed_types
    allow_forward = 'forward' in allowed_types

    msg_type = get_message_type(msg)
    forward = bool(msg.forward_date)
    logger.debug(f"msg_type: {msg_type}, forward: {forward}")

    if force > 0 or msg_type in allowed_types or forward and allow_forward:
        process_message(
            update,
            context,
            msg_type,
            chat,
            anonymous,
            buttons,
            repost=force > 1,
        )


@message_handler(Filters.private & (Filters.text | Filters.sticker) & StateFilter.reaction)
def handle_reaction_response(update: Update, context: CallbackContext):
    user: TGUser = update.effective_user
    msg = update.effective_message
    reaction = msg.text or (msg.sticker and msg.sticker.emoji)

    if reaction not in UNICODE_EMOJI:
        msg.reply_text(f"Reaction should be a single emoji.")
        return

    some_message_id = redis.get_key(user.id, 'message_id')
    try:
        message = Message.objects.prefetch_related().get(id=some_message_id)
    except Message.DoesNotExist:
        logger.debug(f"Message {some_message_id} doesn't exist.")
        msg.reply_text(f"Received invalid message ID from /start command.")
        return

    mids = message.ids
    _, button = Reaction.objects.react(
        user=user,
        button_text=reaction,
        **mids,
    )
    if not button:
        msg.reply_text(f"Post already has too many reactions.")
        return
    reactions = Button.objects.reactions(**mids)
    _, reply_markup = make_reply_markup_from_chat(update, context, reactions, message=message)
    context.bot.edit_message_reply_markup(reply_markup=reply_markup, **mids)
    msg.reply_text(f"Reacted with {reaction}")


@message_handler(Filters.private & StateFilter.create_start)
def handle_create_start(update: Update, context: CallbackContext):
    user: TGUser = update.effective_user
    msg: TGMessage = update.effective_message
    redis.set_key(user, 'message', msg.to_dict())

    # todo: get button from user preferences
    msg.reply_text(
        "Now specify buttons.",
        reply_markup=ReplyKeyboardMarkup.from_column(
            [
                '👍 👎',
                '✅ ❌',
                'none',
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    )
    redis.set_state(user, State.create_buttons)


@message_handler(Filters.private & Filters.text & StateFilter.create_buttons)
def handle_create_buttons(update: Update, context: CallbackContext):
    user: TGUser = update.effective_user
    msg: TGMessage = update.effective_message

    if msg.text == 'none':
        buttons = []
    else:
        buttons = clear_buttons(msg.text.split(), emojis=True)
        if not buttons:
            msg.reply_text("Buttons should be emojis.")
            return
    # todo: save buttons in user preferences for future use
    redis.set_key(user, 'buttons', buttons)
    original_msg = redis.get_json(user.id, 'message')

    context.bot.send_message(
        chat_id=msg.chat_id,
        text=(
            "Press 'publish' and choose chat/channel.\n"
            "Publishing will be available for 1 hour."
        ),
        reply_to_message_id=original_msg['message_id'],
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                "publish",
                switch_inline_query="publish",
            )
        )
    )
    redis.set_state(user, State.create_end)
