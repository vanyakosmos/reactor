import logging
from uuid import uuid4

from telegram import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    ParseMode,
    Update,
    User as TGUser,
)
from telegram.ext import CallbackContext

from bot import redis
from core.models import Message
from .markup import make_reply_markup, make_reply_markup_from_chat
from .utils import chosen_inline_handler, get_user, inline_query_handler
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
    logger.debug('INLINE QUERY')
    logger.debug(update)
    user: TGUser = update.effective_user

    if not creation_filter.filter_by_user(update.effective_user):
        logger.debug("Not at creation state.")
        return
    msg, buttons = redis.get_creation(user.id, context.bot)

    reply_markup = make_reply_markup(context.bot, get_reactions(buttons))

    # todo: setup proper type for QueryResult
    content = msg.text_markdown or msg.caption_markdown
    results = [
        InlineQueryResultArticle(
            id=str(uuid4()),
            title="Message to publish",
            input_message_content=InputTextMessageContent(
                content,
                parse_mode=ParseMode.MARKDOWN,
            ),
            reply_markup=reply_markup,
        )
    ]
    update.inline_query.answer(results, cache_time=0, is_personal=True)


@chosen_inline_handler()
def handle_publishing(update: Update, context: CallbackContext):
    logger.debug('CHOSEN INLINE QUERY')
    logger.debug(update)

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
    context.bot.edit_message_reply_markup(
        reply_markup=reply_markup,
        inline_message_id=inline_id,
    )
