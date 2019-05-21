import logging

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
        Message.objects.create_from_tg_ids(
            sent_msg.chat_id,
            sent_msg.message_id,
            date=msg.date,
            original_message_id=msg.message_id,
            from_user=get_user(update),
            forward_from=get_forward_from(msg),
            forward_from_chat=get_forward_from_chat(msg),
            forward_from_message_id=msg.forward_from_message_id,
        )
        # todo: edit with vote button if channel


@message_handler(
    Filters.group &
    (Filters.photo | Filters.video | Filters.animation | Filters.forwarded | Filters.text) &
    ~Filters.status_update.left_chat_member
)
def handle_message(update: Update, context: CallbackContext):
    msg = update.effective_message

    chat = get_chat_from_tg_chat(update.effective_chat)
    allowed_types = chat.allowed_types
    allow_forward = 'forward' in allowed_types

    msg_type = get_message_type(msg)
    forward = bool(msg.forward_date)

    if msg_type in allowed_types or forward and allow_forward:
        process_message(update, context, msg_type, chat)


@message_handler(Filters.private & Filters.text & reaction_filter)
def handle_reaction_response(update: Update, context: CallbackContext):
    user: TGUser = update.effective_user
    msg = update.effective_message
    reaction = msg.text

    # todo: validate reaction

    some_message_id = redis.awaited_reaction(user.id).decode()
    logger.debug(update)
    logger.debug(some_message_id)
    try:
        message = Message.objects.prefetch_related().get(id=some_message_id)
    except Message.DoesNotExist:
        logger.debug(f"Message {some_message_id} doesn't exist.")
        return

    mids = message.ids

    Button.objects.create_for_reaction(reaction, **mids)
    Reaction.objects.react(
        user_id=user.id,
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
    redis.save_creation(user.id, msg.to_dict(), ['👍', '👎'])
    msg.reply_text(
        "Press 'publish' and choose your channel. Publishing will be available for 1 hour.",
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                "publish",
                switch_inline_query="publish",
            )
        )
    )
