import logging

from telegram import Update
from telegram.ext import CallbackContext, Filters

from core.models import Chat, Message as MessageModel
from .markup import get_reply_markup
from .utils import message_handler, try_delete

logger = logging.getLogger(__name__)


def process_message(update: Update, context: CallbackContext, msg_type: str):
    msg = update.effective_message
    bot = context.bot

    chat, _ = Chat.objects.get_or_create(id=msg.chat_id)
    reply_markup = get_reply_markup(bot, chat.reactions())

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
        MessageModel.objects.create(sent_msg.chat_id, sent_msg.message_id)


@message_handler(
    Filters.group & (Filters.photo | Filters.video | Filters.animation | Filters.forwarded) &
    ~Filters.status_update.left_chat_member
)
def handle_message(update: Update, context: CallbackContext):
    msg = update.effective_message

    allowed_types = {'photo', 'video', 'animation', 'link'}
    allow_forward = True

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
        process_message(update, context, msg_type)
