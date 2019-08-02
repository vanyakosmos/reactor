from telegram import Update
from telegram.ext import Filters, CallbackContext

from bot.wrapper import command
from core.models import Chat
from stats.models import PopularReactions, TopPosters


@command(('reactions', 'reacts'), filters=Filters.group)
def command_reactions(update: Update, _: CallbackContext):
    chat = Chat.objects.from_update(update)
    text = '\n'.join([
        f"{i + 1}. {r.text} -> {r.count}" for i, r in enumerate(PopularReactions.get(chat))
    ])
    text = f"most popular reactions:\n```\n{text}\n```"
    update.message.reply_markdown(text)


@command(('champions', 'champs'), filters=Filters.group)
def command_champions(update: Update, _: CallbackContext):
    chat = Chat.objects.from_update(update)
    text = '\n'.join([
        f"{i + 1}. {p.user.full_name} -> messages: {p.messages}, reactions: {p.reactions}"
        for i, p in enumerate(TopPosters.get(chat))
    ])
    text = f"top posters:\n```\n{text}\n```"
    update.message.reply_markdown(text)
