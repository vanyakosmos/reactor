import logging
from collections import OrderedDict

from telegram import (
    InlineKeyboardButton,
    Message as TGMessage,
    ReplyKeyboardMarkup,
    Update,
    User as TGUser,
)
from telegram.ext import CallbackContext, Filters

from bot import redis
from bot.filters import StateFilter
from bot.markup import make_reactions_keyboard
from bot.redis import State
from bot.utils import clear_buttons, get_message_type, repost_message
from bot.wrapper import message_handler
from core.models import MessageToPublish, UserButtons

logger = logging.getLogger(__name__)


@message_handler(Filters.private & StateFilter.create_start)
def handle_create_start(update: Update, _: CallbackContext):
    user: TGUser = update.effective_user
    msg: TGMessage = update.effective_message
    MessageToPublish.objects.create(user_id=user.id, message=msg.to_dict())

    buttons = [
        *UserButtons.buttons_list(user.id),
        '👍 👎',
        '✅ ❌',
    ]
    buttons = list(OrderedDict.fromkeys(buttons))  # remove duplicated buttons
    buttons = buttons[:3]
    msg.reply_text(
        "Now specify buttons.",
        reply_markup=ReplyKeyboardMarkup.from_column(
            [
                *buttons,
                'none',
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    )
    redis.set_state(user, State.create_buttons)


@message_handler(Filters.private & Filters.text & StateFilter.create_buttons)
def handle_create_buttons(update: Update, context: CallbackContext):
    """
    Save picked buttons to message-to-publish object.
    Send publishable post.
    """
    user: TGUser = update.effective_user
    msg: TGMessage = update.effective_message

    if msg.text == 'none':
        buttons = []
    else:
        buttons = clear_buttons(msg.text.split(), emojis=True)
        if not buttons:
            msg.reply_text("Buttons should be emojis.")
            return
        UserButtons.create(user.id, buttons)

    mtp = MessageToPublish.last(user.id)
    mtp.buttons = buttons
    mtp.save()

    msg.reply_text("Press 'publish' and choose chat/channel.")
    message = mtp.message_tg
    msg_type = get_message_type(message)
    reply_markup = make_reactions_keyboard(buttons, blank=True)
    reply_markup.inline_keyboard.append([
        InlineKeyboardButton(
            "publish",
            switch_inline_query=str(mtp.id),
        )
    ])
    repost_message(message, context.bot, msg_type, reply_markup)
    redis.set_state(user, State.create_end)
