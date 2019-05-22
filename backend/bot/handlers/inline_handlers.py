import logging
from uuid import uuid4

from telegram import (
    InlineQueryResultArticle,
    InlineQueryResultCachedPhoto,
    InlineQueryResultCachedMpeg4Gif,
    InlineQueryResultCachedVideo,
    InputTextMessageContent,
    ParseMode,
    Update,
    User as TGUser,
)
from telegram.error import BadRequest
from telegram.ext import CallbackContext

from bot import redis
from core.models import Message
from .markup import make_reply_markup, make_reply_markup_from_chat
from .utils import chosen_inline_handler, get_user, inline_query_handler, get_message_type
from .filters import creation_filter

logger = logging.getLogger(__name__)


def get_reactions(buttons):
    return [{
        'index': index,
        'text': text,
        'count': 0,
    } for index, text in enumerate(buttons)]


@inline_query_handler(pattern='publish')
def handle_publishing_options(update: Update, context: CallbackContext):
    user: TGUser = update.effective_user

    if not creation_filter.filter_by_user(update.effective_user):
        logger.debug("Not at creation state.")
        return
    msg, buttons = redis.get_creation(user.id, context.bot)

    reply_markup = make_reply_markup(context.bot, get_reactions(buttons))

    msg_type = get_message_type(msg)
    config = {
        'id': str(uuid4()),
        'title': "Message to publish",
        'text': msg.text_markdown,
        'caption': msg.caption_markdown,
        'parse_mode': ParseMode.MARKDOWN,
        'reply_markup': reply_markup,
        # types
        'photo_file_id': msg.photo and msg.photo[0].file_id,
        'video_file_id': msg.video and msg.video.file_id,
        'mpeg4_file_id': msg.animation and msg.animation.file_id,
    }
    if msg_type == 'photo':
        qr = InlineQueryResultCachedPhoto(**config)
    elif msg_type == 'video':
        qr = InlineQueryResultCachedVideo(**config)
    elif msg_type == 'animation':
        qr = InlineQueryResultCachedMpeg4Gif(**config)
    elif msg_type in ('text', 'link'):
        qr = InlineQueryResultArticle(
            input_message_content=InputTextMessageContent(
                msg.text_markdown,
                parse_mode=ParseMode.MARKDOWN,
            ),
            **config,
        )
    else:
        return
    update.inline_query.answer([qr], cache_time=0, is_personal=True)


@chosen_inline_handler()
def handle_publishing(update: Update, context: CallbackContext):
    res = update.chosen_inline_result
    if res.query != 'publish':
        return
    inline_id = res.inline_message_id
    if not inline_id:
        logger.exception("Invalid inline query.")
        return

    user: TGUser = update.effective_user
    msg, buttons = redis.get_creation(user.id, context.bot)
    message = Message.objects.create_from_inline(
        inline_message_id=inline_id,
        buttons=buttons,
        from_user=get_user(update),
    )
    _, reply_markup = make_reply_markup_from_chat(
        update,
        context,
        get_reactions(buttons),
        message=message,
    )
    try:
        context.bot.edit_message_reply_markup(
            reply_markup=reply_markup,
            inline_message_id=inline_id,
        )
    except BadRequest:  # message was deleted too fast (probably by the same bot in chat)
        message.delete()
