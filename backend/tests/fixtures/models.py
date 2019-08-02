from typing import Callable

import pytest
from _pytest.fixtures import FixtureRequest
from django.utils import timezone
from telegram import Chat as TGChat

from core.models import Button, Chat, Message, User
from .utils import append_to_cls, get_id


@pytest.fixture(scope='class')
def create_user(request: FixtureRequest) -> Callable:
    def _create_user(**kwargs):
        fields = {
            'id': get_id(),
            'first_name': 'user',
            **kwargs,
        }
        return User.objects.create(**fields)

    return append_to_cls(request, _create_user)


@pytest.fixture(scope='class')
def create_chat(request: FixtureRequest) -> Callable:
    def _create_chat(**kwargs):
        fields = {
            'id': get_id(),
            'type': TGChat.SUPERGROUP,
            **kwargs,
        }
        return Chat.objects.create(**fields)

    return append_to_cls(request, _create_chat)


@pytest.fixture(scope='class')
def create_message(request: FixtureRequest, create_user) -> Callable:
    def _create_message(buttons=None, from_user=None, **kwargs):
        # if chat is not specified - assume inline message
        inline = not bool(kwargs.get('chat') or kwargs.get('chat_id'))
        msg_id = ('id' in kwargs and kwargs.pop('id')) or get_id()
        if not inline:
            chat_id = kwargs.get('chat_id') or kwargs.get('chat').id
            msg_id = Message.get_id(chat_id, msg_id)
        fields = {
            'id': msg_id,
            'date': timezone.now(),
            'from_user': from_user or create_user(),
            'inline_message_id': msg_id if inline else None,
            **kwargs,
        }
        msg = Message.objects.create(**fields)
        if buttons:
            msg.set_buttons(buttons)
        return msg

    return append_to_cls(request, _create_message)


@pytest.fixture(scope='class')
def create_button(request: FixtureRequest, create_message) -> Callable:
    def _create_button(emoji=False, message=None, **kwargs):
        fields = {
            'message': message or create_message(),
            'index': 0,
            'text': '👍' if emoji else 'b',
            **kwargs,
        }
        return Button.objects.create(**fields)

    return append_to_cls(request, _create_button)
