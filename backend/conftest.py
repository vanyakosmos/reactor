import uuid
from typing import Callable

import pytest
from _pytest.fixtures import FixtureRequest
from django.utils import timezone
from telegram import Chat as TGChat

from core.models import Button, Chat, Message, User


def append_to_cls(request: FixtureRequest, func, name=None):
    name = name or func.__name__.strip('_')
    setattr(request.cls, name, staticmethod(func))
    return func


def get_id():
    # generate 128 bit number and shift it by 64
    return str(uuid.uuid1().int >> 64)


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
    def _create_message(**kwargs):
        # if chat is not specified - assume inline message
        inline = not bool(kwargs.get('chat') or kwargs.get('chat_id'))
        msg_id = get_id()
        if not inline:
            chat_id = kwargs.get('chat_id') or kwargs.get('chat').id
            msg_id = Message.get_id(chat_id, msg_id)
        fields = {
            'id': msg_id,
            'date': timezone.now(),
            'from_user': create_user(),
            'inline_message_id': msg_id if inline else None,
            **kwargs,
        }
        return Message.objects.create(**fields)

    return append_to_cls(request, _create_message)


@pytest.fixture(scope='class')
def create_button(request: FixtureRequest, create_message) -> Callable:
    def _create_button(emoji=False, **kwargs):
        fields = {
            'message': create_message(),
            'index': 0,
            'text': '👍' if emoji else 'b',
            **kwargs,
        }
        return Button.objects.create(**fields)

    return append_to_cls(request, _create_button)
