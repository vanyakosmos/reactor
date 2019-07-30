import logging

from emoji import UNICODE_EMOJI
from telegram import Message as TGMessage, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext, Filters

from bot.filters import reply_to_bot
from bot.magic_marks import process_magic_mark
from bot.markup import make_reply_markup_from_chat
from bot.utils import try_delete
from bot.wrapper import message_handler
from core.models import Button, Message, Reaction

logger = logging.getLogger(__name__)


def get_msg(reply: TGMessage):
    try:
        return Message.objects.prefetch_related().get_by_ids(reply.chat_id, reply.message_id)
    except Message.DoesNotExist:
        logger.debug(f"message doesn't exist. reply: {reply}")


def update_markup(update, context, message, tg_message, reply):
    reactions = Button.objects.reactions(reply.chat_id, reply.message_id)
    _, reply_markup = make_reply_markup_from_chat(update, context, reactions, message=message)
    try:
        reply.edit_reply_markup(reply_markup=reply_markup)
    except BadRequest as e:
        logger.debug(f"message was not modified (chat.repost=false, toggle anonymity): {e}")
    try_delete(context.bot, update, tg_message)


@message_handler(
    Filters.group & Filters.reply & reply_to_bot & Filters.text & Filters.regex(r'^\+(.+)')
)
def handle_reaction_reply(update: Update, context: CallbackContext):
    user = update.effective_user
    msg = update.effective_message
    reaction = context.match[1]
    reply = msg.reply_to_message

    message = get_msg(reply)
    if not message:
        return

    if not message.chat.allow_reactions:
        logger.debug("reactions are not allowed")
        return

    if message.chat.force_emojis and reaction not in UNICODE_EMOJI:
        logger.debug("can't react with non-emoji text")
        return

    _, button = Reaction.objects.react(
        user=user,
        chat_id=reply.chat_id,
        message_id=reply.message_id,
        inline_message_id=None,
        button_text=reaction,
    )
    if not button:
        msg.reply_text("Post already has too many reactions.")
        return

    update_markup(update, context, message, msg, reply)


@message_handler(
    Filters.group & Filters.reply & reply_to_bot & Filters.text & Filters.regex(r'^\.(.+)')
)
def handle_magic_reply(update: Update, context: CallbackContext):
    user = update.effective_user
    msg = update.effective_message
    reply = msg.reply_to_message

    _, anonymous, _, buttons = process_magic_mark(msg)
    logger.debug(f"anonymous={anonymous}, buttons={buttons}")

    if not anonymous and buttons is None:
        logger.debug("nothing to do here")
        return

    message = get_msg(reply)
    if not message:
        return

    if str(message.from_user.id) != str(user.id):
        logger.debug(f"OP and replier doesn't match: {message.from_user.id} vs {user.id}")
        return

    if anonymous:
        message.anonymous = not message.anonymous
        message.save()

    if buttons is not None:
        message.button_set.all().delete()
        message.set_buttons(buttons)

    update_markup(update, context, message, msg, reply)
