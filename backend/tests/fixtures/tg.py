from typing import Callable
from unittest.mock import Mock

import pytest
from _pytest.fixtures import FixtureRequest
from django.conf import settings
from telegram import (
    Chat as TGChat,
    User as TGUser,
    Message as TGMessage,
    Update,
    Bot,
)

from .utils import append_to_cls, get_id, decode_tg_object


@pytest.fixture(scope='class')
def create_tg_user(request: FixtureRequest) -> Callable:
    def _create_tg_user(**kwargs):
        fields = {
            'id': get_id(),
            'first_name': 'user',
            'is_bot': False,
            **kwargs,
        }
        return TGUser(**fields)

    return append_to_cls(request, _create_tg_user)


@pytest.fixture(scope='class')
def create_tg_chat(request: FixtureRequest) -> Callable:
    def _create_tg_chat(**kwargs):
        data = {
            'id': -100000000000,
            'type': TGChat.SUPERGROUP,
            'title': 'test chat',
            'username': 'testchat',
            **kwargs,
        }
        return TGChat.de_json(data, bot=None)

    return append_to_cls(request, _create_tg_chat)


@pytest.fixture(scope='class')
def create_tg_message(
    request: FixtureRequest, create_bot, create_tg_user, create_tg_chat
) -> Callable:
    def _create_tg_message(bot=None, user=None, chat=None, **kwargs):
        bot = bot or create_bot()
        user = decode_tg_object(user, create_tg_user().to_dict())
        chat = decode_tg_object(chat, create_tg_chat().to_dict())
        data = {
            'message_id': get_id(),
            'date': 1564646464,
            'from': user,
            'chat': chat,
            **kwargs,
        }
        return TGMessage.de_json(data, bot)

    return append_to_cls(request, _create_tg_message)


@pytest.fixture(scope='class')
def create_bot(request: FixtureRequest) -> Callable:
    def _create_bot():
        return Bot(settings.TG_BOT_TOKEN)

    return append_to_cls(request, _create_bot)


@pytest.fixture(scope='class')
def create_context(request, create_bot):
    def _create_context(bot=None, args=None, match=None, message: TGMessage = None):
        if message and message.text and message.text.startswith('/'):
            args = args or message.text.split()[1:]
        context = Mock()
        context.bot = bot or create_bot()
        context.args = args or []
        context.match = match or []
        return context

    return append_to_cls(request, _create_context)


def create_inline_query(user):
    return {
        'id': '384826580849189586',
        'query': '2008679b-6e3d-4d25-810f-c25c073dbde7',
        'offset': '',
        'from': user
    }


def create_chosen_inline_result(user):
    return {
        'result_id': '3951f204-53c7-4cd4-ba36-886342e979b7',
        'query': '2008679b-6e3d-4d25-810f-c25c073dbde7',
        'inline_message_id': 'AgAAAKlCAABX4ui8j5MPpV3dwRg',
        'from': user,
    }


def create_callback_query(user, message, data='~'):
    return {
        'id': get_id(),
        'chat_instance': get_id(),
        'inline_message_id': message['message_id'] if not message.get('chat') else None,
        'message': message,
        'data': data,
        'from': user,
    }


@pytest.fixture(scope='class')
def create_update(
    request: FixtureRequest,
    create_bot,
    create_tg_user,
    create_tg_chat,
    create_tg_message,
) -> Callable:
    def _create_update(
        bot=None,
        inline_query=False,
        chosen_inline_result=False,
        callback_query=None,
        user: TGUser = None,
        forward_from: TGChat = None,
        chat: TGChat = None,
        message: TGMessage = None,
        reply_to_message: TGMessage = None,
    ):
        bot = bot or create_bot()
        if message and not user:
            user = message.from_user.to_dict()
        else:
            user = decode_tg_object(user, create_tg_user().to_dict())
        chat = decode_tg_object(chat, create_tg_chat().to_dict())
        message = decode_tg_object(message, create_tg_message(user=user, chat=chat).to_dict())

        update = {'update_id': 486565656}

        if callback_query:
            update['callback_query'] = create_callback_query(user, message, callback_query)

        if inline_query:
            update['inline_query'] = create_inline_query(user)

        if chosen_inline_result:
            update['chosen_inline_result'] = create_chosen_inline_result(user)

        if message:
            if forward_from:
                message['forward_from'] = decode_tg_object(forward_from)

            if reply_to_message:
                message['reply_to_message'] = reply_to_message.to_dict()

        if message and not callback_query:
            update['message'] = message

        return Update.de_json(update, bot)

    return append_to_cls(request, _create_update)
