import logging

from telegram import Update, Message as TGMessage, User as TGUser, Chat as TGChat
from telegram.ext import CallbackContext, Filters

from bot.redis import save_media_group
from core.models import Chat, Message, User
from .markup import make_reply_markup_from_chat
from .utils import message_handler, try_delete

logger = logging.getLogger(__name__)


def get_user(update: Update):
    u: TGUser = update.effective_user
    user, _ = User.objects.update_or_create(
        id=u.id,
        defaults={
            'username': u.username,
            'first_name': u.first_name,
            'last_name': u.last_name,
        },
    )
    return user


def get_forward_from(msg: TGMessage):
    if msg.forward_from:
        u: TGUser = msg.forward_from
        forward, _ = User.objects.update_or_create(
            id=u.id,
            defaults={
                'username': u.username,
                'first_name': u.first_name,
                'last_name': u.last_name,
            },
        )
        return forward


def get_chat_from_tg_chat(tg_chat: TGChat) -> Chat:
    if tg_chat.last_name:
        fallback_name = f'{tg_chat.first_name} {tg_chat.last_name}'
    else:
        fallback_name = tg_chat.first_name
    chat, _ = Chat.objects.update_or_create(
        id=tg_chat.id,
        defaults={
            'type': tg_chat.type,
            'username': tg_chat.username,
            'title': tg_chat.title or fallback_name,
        },
    )
    return chat


def get_forward_from_chat(msg: TGMessage):
    if msg.forward_from_chat:
        return get_chat_from_tg_chat(msg.forward_from_chat)


def process_message(update: Update, context: CallbackContext, msg_type: str, chat: Chat):
    msg: TGMessage = update.effective_message
    bot = context.bot

    chat, reply_markup = make_reply_markup_from_chat(update, context, chat=chat)

    config = {
        'chat_id': msg.chat_id,
        'disable_notification': True,
        'parse_mode': 'HTML',
        'reply_markup': reply_markup,
    }
    if msg_type in ('photo', 'video', 'animation'):
        config['caption'] = msg.caption_html
    if msg_type == 'photo':
        config['photo'] = msg.photo[0].file_id
        sent_msg = bot.send_photo(**config)
    elif msg_type == 'video':
        config['video'] = msg.video.file_id
        sent_msg = bot.send_video(**config)
    elif msg_type == 'animation':
        config['animation'] = msg.animation.file_id
        sent_msg = bot.send_animation(**config)
    elif msg_type == 'text':
        config['text'] = msg.text_html
        sent_msg = bot.send_message(**config)
    elif msg_type == 'album':
        config.pop('chat_id')
        config['text'] = '^'
        sent_msg = msg.reply_text(**config)
    else:
        sent_msg = None

    if sent_msg:
        if msg_type != 'album':
            try_delete(bot, update, msg)
        Message.objects.create(
            sent_msg.chat_id,
            sent_msg.message_id,
            date=msg.date,
            original_message_id=msg.message_id,
            from_user=get_user(update),
            forward_from=get_forward_from(msg),
            forward_from_chat=get_forward_from_chat(msg),
            forward_from_message_id=msg.forward_from_message_id,
        )


@message_handler(
    Filters.group & (Filters.photo | Filters.video | Filters.animation | Filters.forwarded) &
    ~Filters.status_update.left_chat_member
)
def handle_message(update: Update, context: CallbackContext):
    msg = update.effective_message

    chat = get_chat_from_tg_chat(update.effective_chat)
    allowed_types = chat.allowed_types
    allow_forward = 'forward' in allowed_types

    msg_type = 'unknown'
    forward = bool(msg.forward_date)
    if msg.media_group_id:
        if save_media_group(msg.media_group_id):
            msg_type = 'album'
    elif msg.photo:
        msg_type = 'photo'
    elif msg.video:
        msg_type = 'video'
    elif msg.animation:
        msg_type = 'animation'
    elif msg.document:
        msg_type = 'doc'
    elif any((e['type'] == 'url' for e in msg.entities)):
        msg_type = 'link'
    elif msg.text:
        msg_type = 'text'

    if msg_type in allowed_types or forward and allow_forward:
        process_message(update, context, msg_type, chat)
