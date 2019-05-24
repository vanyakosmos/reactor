import logging

from django.utils import timezone
from emoji import UNICODE_EMOJI
from telegram import (
    Update,
    Message as TGMessage,
    User as TGUser,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import CallbackContext, Filters

from bot import redis
from core.models import Button, Chat, Message, Reaction
from .filters import reaction_filter
from .markup import make_reply_markup_from_chat
from .utils import (
    message_handler,
    try_delete,
    get_message_type,
    get_chat_from_tg_chat,
    get_forward_from,
    get_user,
    get_forward_from_chat,
)

logger = logging.getLogger(__name__)


def process_message(
    update: Update,
    context: CallbackContext,
    msg_type: str,
    chat: Chat,
    anonymous: bool,
):
    msg: TGMessage = update.effective_message
    bot = context.bot

    chat, reply_markup = make_reply_markup_from_chat(
        update,
        context,
        chat=chat,
        anonymous=anonymous,
    )

    if chat.repost:
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
        elif msg_type == 'album':
            config.pop('chat_id')
            config['text'] = '^'
            sent_msg = msg.reply_text(**config)
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
        if chat.repost and msg_type != 'album':
            try_delete(bot, update, msg)
        Message.objects.create_from_tg_ids(
            sent_msg.chat_id,
            sent_msg.message_id,
            anonymous=anonymous,
            date=timezone.make_aware(msg.date),
            original_message_id=msg.message_id,
            from_user=get_user(update),
            forward_from=get_forward_from(msg),
            forward_from_chat=get_forward_from_chat(msg),
            forward_from_message_id=msg.forward_from_message_id,
        )


def get_magic_mark(msg: TGMessage):
    text: str = msg.text or msg.caption
    if not text:
        return
    for mark in ('--', '++', '~~', '+~'):
        if text.startswith(mark):
            return mark


def remove_magic_mark(msg: TGMessage, mark: str):
    s = len(mark)
    if msg.text and len(msg.text) > s:
        msg.text = msg.text[s:]
    elif msg.text:
        return False
    if msg.caption and len(msg.caption) > s:
        msg.caption = msg.caption[s:]
    else:
        msg.caption = None
    return True


def process_magic_mark(msg: TGMessage):
    force = False
    anon = False
    skip = False
    mark = get_magic_mark(msg)
    if not mark:
        pass
    elif not remove_magic_mark(msg, mark):
        skip = True
    elif mark == '--':
        skip = True
    elif mark == '++':
        force = True
    elif mark == '~~':
        anon = True
    elif mark == '+~':
        force = True
        anon = True
    return force, anon, skip


@message_handler(Filters.group & ~Filters.reply & ~Filters.status_update)
def handle_message(update: Update, context: CallbackContext):
    msg: TGMessage = update.effective_message

    force, anonymous, skip = process_magic_mark(msg)
    logger.debug(f"force: {force}, anonymous: {anonymous}, skip: {skip}")
    if skip:
        logger.debug('skipping message processing')
        return

    chat = get_chat_from_tg_chat(update.effective_chat)
    allowed_types = chat.allowed_types
    allow_forward = 'forward' in allowed_types

    msg_type = get_message_type(msg)
    forward = bool(msg.forward_date)
    logger.debug(f"msg_type: {msg_type}, forward: {forward}")

    if force or msg_type in allowed_types or forward and allow_forward:
        process_message(update, context, msg_type, chat, anonymous)


@message_handler(Filters.private & Filters.text & reaction_filter)
def handle_reaction_response(update: Update, context: CallbackContext):
    user: TGUser = update.effective_user
    msg = update.effective_message
    reaction = msg.text

    if reaction not in UNICODE_EMOJI:
        msg.reply_text(f"Reaction should be a single emoji.")
        return

    some_message_id = redis.awaited_reaction(user.id)
    try:
        message = Message.objects.prefetch_related().get(id=some_message_id)
    except Message.DoesNotExist:
        logger.debug(f"Message {some_message_id} doesn't exist.")
        return

    mids = message.ids
    Reaction.objects.react(
        user=user,
        button_text=reaction,
        **mids,
    )
    reactions = Button.objects.reactions(**mids)
    _, reply_markup = make_reply_markup_from_chat(update, context, reactions, message=message)
    context.bot.edit_message_reply_markup(reply_markup=reply_markup, **mids)
    msg.reply_text(f"Reacted with {reaction}")
    redis.stop_awaiting_reaction(user.id)


@message_handler(
    Filters.private &
    (Filters.photo | Filters.video | Filters.animation | Filters.forwarded | Filters.text)
)
def handle_create(update: Update, context: CallbackContext):
    user: TGUser = update.effective_user
    msg: TGMessage = update.effective_message
    # todo: ask user for buttons and other settings
    redis.save_creation(user.id, msg.to_dict(), ['👍', '👎'])
    msg.reply_text(
        "Press 'publish' and choose your channel.\n"
        "Publishing will be available for 1 hour.",
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                "publish",
                switch_inline_query="publish",
            )
        )
    )
