import logging
import re

from django.utils.datastructures import OrderedSet
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Message, ParseMode, Update
from telegram.ext import CallbackContext, Filters

from .utils import command, get_chat, message_handler, try_delete
from core.models import Chat, Message as MessageModel, Reaction, Button

logger = logging.getLogger(__name__)


def handle_error(update: Update, context: CallbackContext):
    logger.warning(f"🔥 Update {update}\n   caused error: {context.error}")


@command('help')
def command_help(update: Update, context: CallbackContext):
    text = '\n'.join([
        "This bot will automagically add reactions panel to your images/gifs/videos/links.",
        "`/help` - print this message",
        "`/set <button> [<button>...]` - set up buttons",
        "`/get` - get list of default buttons for this chat",
    ])
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@command('get')
def command_get_buttons(update: Update, context: CallbackContext):
    chat = get_chat(update)
    bs = ', '.join(chat.buttons)
    update.message.reply_text(f"Current default buttons: [{bs}]")


@command('set', pass_args=True)
def command_set_buttons(update: Update, context: CallbackContext):
    chat = get_chat(update)
    if len(context.args) > 80:
        update.message.reply_text("Number of buttons is too big.")
        return
    bs = [b for b in OrderedSet(context.args) if len(b) < 20]
    chat.buttons = bs
    chat.save()
    bs = ', '.join(bs)
    update.message.reply_text(f"New default buttons: [{bs}]")


@message_handler(Filters.status_update.new_chat_members)
def handle_new_member(update: Update, context: CallbackContext):
    msg = update.effective_message
    for member in msg.new_chat_members:
        if member.id == context.bot.id:
            Chat.objects.get_or_create(id=msg.chat_id)


def reply_to_reaction(bot, query, button, reaction):
    if reaction:
        reply = f"You reacted {button.text}"
    else:
        reply = "You removed reaction"
    bot.answer_callback_query(query.id, reply)


def handle_button_callback(update: Update, context: CallbackContext):
    msg = update.effective_message
    user = update.effective_user
    query = update.callback_query

    try:
        reaction, button = Reaction.objects.react(
            user_id=user.id,
            chat_id=msg.chat_id,
            message_id=msg.message_id,
            button_text=query.data,
        )
        reply_to_reaction(context.bot, query, button, reaction)
        reactions = Button.objects.reactions(msg.chat_id, msg.message_id)
        reply_markup = get_reply_markup(reactions)
        msg.edit_reply_markup(reply_markup=reply_markup)
    except Exception as e:
        logger.exception(e)


def process_message(update: Update, context: CallbackContext, msg_type: str):
    msg = update.effective_message
    bot = context.bot

    try_delete(bot, update, msg)

    chat, _ = Chat.objects.get_or_create(id=msg.chat_id)

    if msg_type == 'photo':
        reply_markup = get_reply_markup(chat.reactions())
        sent_msg = bot.send_photo(
            chat_id=msg.chat_id,
            caption=msg.caption_html,
            disable_notification=True,
            parse_mode='HTML',
            reply_markup=reply_markup,
            photo=msg.photo[0].file_id,
        )
        MessageModel.objects.create(sent_msg.chat_id, sent_msg.message_id)

        # send_media(msg_model, msg, bot.send_photo, {'photo': msg.photo[0].file_id})
    # elif msg_type == 'video':
    #     send_media(msg_model, msg, bot.send_video, {'video': msg.video.file_id})
    # else:
    #     send_text(msg_model, msg, bot)


def get_reply_markup(rates: list):
    keys = []
    for rate in rates:
        text = rate['text']
        count = rate['count']
        payload = rate['text']
        if count:
            text = f'{text} {count}'
        keys.append(InlineKeyboardButton(text, callback_data=payload))

    keyboard = []
    max_cols = 4
    while keys:
        keyboard += [keys[:max_cols]]
        keys = keys[max_cols:]

    return InlineKeyboardMarkup(keyboard)


def send_media(msg_model: MessageModel, message: Message, sender, file: dict):
    # todo: account forward
    reply_markup = get_reply_markup(msg_model.reactions())
    sender(
        chat_id=message.chat_id,
        caption=message.caption_html,
        disable_notification=True,
        parse_mode='HTML',
        reply_markup=reply_markup,
        **file,
    )


def send_text(msg_model: MessageModel, message: Message, bot: Bot):
    reply_markup = get_reply_markup(msg_model.reactions())
    bot.send_message(
        chat_id=message.chat_id,
        text=message.text_html,
        disable_notification=True,
        parse_mode='HTML',
        reply_markup=reply_markup,
    )


@message_handler(Filters.reply & Filters.text)
def handle_reply(update: Update, context: CallbackContext):
    user = update.effective_user
    msg = update.effective_message
    match = re.match(r'\+(\w+)', msg.text)
    if not match:
        return
    reaction = match[1]
    try_delete(context.bot, update, msg)

    reply = msg.reply_to_message
    umid = MessageModel.get_id(reply.chat_id, reply.message_id)
    try:
        Button.objects.get(message_id=umid, text=reaction)
    except Button.DoesNotExist:
        b = Button.objects.filter_by_message(reply.chat_id, reply.message_id).last()
        Button.objects.create(message_id=umid, text=reaction, index=b.index + 1)

    Reaction.objects.react(
        user_id=user.id,
        chat_id=reply.chat_id,
        message_id=reply.message_id,
        button_text=reaction,
    )
    reactions = Button.objects.reactions(reply.chat_id, reply.message_id)
    reply_markup = get_reply_markup(reactions)
    reply.edit_reply_markup(reply_markup=reply_markup)


@message_handler(
    Filters.group & (Filters.photo | Filters.video | Filters.text | Filters.forwarded) &
    ~Filters.status_update.left_chat_member
)
def handle_message(update: Update, context: CallbackContext):
    msg = update.effective_message

    allowed_types = {'photo', 'video', 'link'}
    allow_forward = True

    forward = bool(msg.forward_date)
    if msg.media_group_id:
        msg_type = 'album'
    elif msg.photo:
        msg_type = 'photo'
    elif msg.video:
        msg_type = 'video'
    elif msg.document:
        msg_type = 'doc'
    # todo
    # elif msg.text is link:
    #     pass
    elif msg.text:
        msg_type = 'text'
    else:
        msg_type = 'unknown'
    context.bot.send_message(msg.chat_id, f"msg_type: {msg_type}, forward: {forward}")
    if msg_type in allowed_types or forward and allow_forward:
        try:
            process_message(update, context, msg_type)
        except Exception as e:
            logger.exception(e)
