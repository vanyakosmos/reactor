from django.utils.datastructures import OrderedSet
from emoji import UNICODE_EMOJI
from telegram import Bot, Message as TGMessage, Update, User as TGUser

from bot.consts import MESSAGE_TYPES, MAX_BUTTON_LEN
from bot.mwt import MWT
from bot.redis import save_media_group
from core.models import Chat, User


def get_chat(update) -> Chat:
    return Chat.objects.get_or_create(id=str(update.effective_chat.id))[0]


@MWT(timeout=60)
def get_admin_ids(bot, chat_id):
    """Returns a set of admin IDs for a given chat. Results are cached for 1 minute."""
    return {admin.user.id for admin in bot.get_chat_administrators(chat_id)}


def user_is_chat_admin(bot, user_id, chat_id):
    return user_id in get_admin_ids(bot, chat_id)


def user_is_admin(bot, update: Update):
    return user_is_chat_admin(bot, update.effective_user.id, update.effective_chat.id)


def bot_is_admin(bot, update):
    return user_is_chat_admin(bot, bot.id, update.effective_chat.id)


def try_delete(bot, update, msg):
    if bot_is_admin(bot, update):
        msg.delete()


def get_message_type(msg: TGMessage):
    if msg.media_group_id:
        if save_media_group(msg.media_group_id):
            return 'album'
        return
    if any((e['type'] == 'url' for e in msg.entities)):
        return 'link'
    for field in MESSAGE_TYPES:
        if getattr(msg, field, None):
            return field


def get_forward_from(msg: TGMessage):
    if msg.forward_from:
        u: TGUser = msg.forward_from
        return User.objects.from_tg_user(u)


def get_forward_from_chat(msg: TGMessage):
    if msg.forward_from_chat:
        return Chat.objects.from_tg_chat(msg.forward_from_chat)


def clear_buttons(buttons: list, emojis=False):
    buttons = [b for b in OrderedSet(buttons) if len(b) < MAX_BUTTON_LEN]
    if emojis and not all([b in UNICODE_EMOJI for b in buttons]):
        return
    return buttons


def repost_message(msg: TGMessage, bot: Bot, msg_type, reply_markup):
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
    return sent_msg
