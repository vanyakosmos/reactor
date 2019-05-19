import logging

from telegram import Update, Message
from telegram.ext import CallbackContext, Filters

from core.models import Chat, Message as MessageModel, TGUser
from .markup import make_reply_markup_from_chat
from .utils import message_handler, try_delete

logger = logging.getLogger(__name__)


def get_user(update: Update):
    u = update.effective_user
    user, _ = TGUser.objects.get_or_create(
        id=u.id,
        defaults={
            'username': u.username,
            'name': u.full_name,
        },
    )
    return user


def get_forward_user(msg: Message):
    if msg.forward_from:
        f = msg.forward_from
        forward, _ = TGUser.objects.get_or_create(
            id=f.id,
            defaults={
                'username': f.username,
                'name': f.full_name,
            },
        )
    elif msg.forward_from_chat:
        f = msg.forward_from_chat
        forward, _ = TGUser.objects.get_or_create(
            id=f.id,
            defaults={
                'username': f.username,
                'name': f.title,
            },
        )
    else:
        forward = None
    return forward


def process_message(update: Update, context: CallbackContext, msg_type: str, chat: Chat):
    msg = update.effective_message
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
    else:
        sent_msg = None

    if sent_msg:
        try_delete(bot, update, msg)
        MessageModel.objects.create(
            sent_msg.chat_id,
            sent_msg.message_id,
            original_message_id=msg.message_id,
            forward_from_message_id=msg.forward_from_message_id,
            from_user=get_user(update),
            from_forward=get_forward_user(msg),
        )


@message_handler(
    Filters.group & (Filters.photo | Filters.video | Filters.animation | Filters.forwarded) &
    ~Filters.status_update.left_chat_member
)
def handle_message(update: Update, context: CallbackContext):
    msg = update.effective_message

    chat, _ = Chat.objects.get_or_create(id=msg.chat_id)
    allowed_types = chat.allowed_types
    allow_forward = 'forward' in allowed_types

    forward = bool(msg.forward_date)
    if msg.media_group_id:
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
    else:
        msg_type = 'unknown'
    if msg_type in allowed_types or forward and allow_forward:
        process_message(update, context, msg_type, chat)
