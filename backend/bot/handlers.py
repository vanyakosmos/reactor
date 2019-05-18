import logging

from django.utils.datastructures import OrderedSet
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Message, ParseMode, Update
from telegram.ext import CallbackContext

from bot.utils import bot_is_admin, command, get_chat
from core.models import Chat, Message as MessageModel, Reaction

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
    bs = ', '.join(chat.keyboard.buttons)
    update.message.reply_text(f"Current default buttons: {bs}")


@command('set', pass_args=True)
def command_set_buttons(update: Update, context: CallbackContext):
    chat = get_chat(update)
    if len(context.args) == 0:
        update.message.reply_text("Buttons were not specified.")
        return
    if len(context.args) > 80:
        update.message.reply_text("Number of buttons is too big.")
        return
    bs = [b for b in OrderedSet(context.args) if len(b) < 20]
    if len(bs) == 0:
        update.message.reply_text("All of the specified buttons are invalid.")
        return
    chat.set_keyboard(bs)
    bs = ', '.join(bs)
    update.message.reply_text(f"New default buttons: {bs}")


def handle_button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    msg = query.message
    # msg_model = MessageModel.objects.get_by_ids(msg.chat_id, msg.message_id)

    button_id, count = map(int, query.data.split(':'))
    r = Reaction.objects.react(
        user_id=query['from'].id,
        chat_id=msg.chat_id,
        message_id=msg.message_id,
        button_id=button_id,
    )
    # todo: resend message
    print(r)
    context.bot.answer_callback_query(query.id, 'ok')


def process_message(update: Update, context: CallbackContext, msg_type: str):
    msg = update.effective_message
    bot = context.bot

    if bot_is_admin(bot, update):
        msg.delete()

    Chat.objects.get_or_create(id=msg.chat_id)
    msg_model = MessageModel.objects.create(msg.chat_id, msg.message_id)

    if msg_type == 'photo':
        send_media(msg_model, msg, bot.send_photo, {'photo': msg.photo[0].file_id})
    elif msg_type == 'video':
        send_media(msg_model, msg, bot.send_video, {'video': msg.video.file_id})
    else:
        send_text(msg_model, msg, bot)


def get_reply_markup(original_message: Message, rates: list):
    keys = []
    # sorted_bs = sorted(rates.keys(), key=lambda x: rates[x]['pos'])
    for rate in rates:
        button_id = rate['id']
        text = rate['text']
        count = rate['count']
        if count:
            text = f'{text} {count}'
        payload = f'{button_id}:{count}'
        keys.append(InlineKeyboardButton(text, callback_data=payload))

    print(rates, keys)
    keyboard = []
    # if original_message:
    #     keyboard.append(sign_buttons(original_message))

    max_cols = 3
    while keys:
        keyboard += [keys[:max_cols]]
        keys = keys[max_cols:]

    return InlineKeyboardMarkup(keyboard)


def send_media(msg_model: MessageModel, message: Message, sender, file: dict):
    # todo: account forward
    reply_markup = get_reply_markup(message, msg_model.reactions())
    print(reply_markup)
    sender(
        chat_id=message.chat_id,
        caption=message.caption_html,
        disable_notification=True,
        parse_mode='HTML',
        reply_markup=reply_markup,
        **file,
    )


def send_text(msg_model: MessageModel, message: Message, bot: Bot):
    reply_markup = get_reply_markup(message, msg_model.reactions())
    bot.send_message(
        chat_id=message.chat_id,
        text=message.text_html,
        disable_notification=True,
        parse_mode='HTML',
        reply_markup=reply_markup,
    )


def handle_message(update: Update, context: CallbackContext):
    print(update)
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
            print(e)
