import json

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from telegram import Update, Bot
from telegram.ext import Dispatcher

from bot.dispatcher import setup_dispatcher

if settings.WEBHOOK_URL:
    bot = Bot(settings.TG_BOT_TOKEN)
    dispatcher = Dispatcher(bot, update_queue=None, use_context=True)
    setup_dispatcher(dispatcher, inspect=True)


@csrf_exempt
def process_update_view(request: HttpRequest):
    if request.method == 'POST':
        data = json.loads(request.body)
        update = Update.de_json(data, bot)
        dispatcher.process_update(update)
    return HttpResponse()
