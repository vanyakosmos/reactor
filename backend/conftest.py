from time import time
from typing import Callable

from telegram import Chat as TGChat
import pytest
from _pytest.fixtures import FixtureRequest

from core.models import User, Chat


@pytest.fixture(scope='class')
def create_user(request: FixtureRequest) -> Callable:
    def _create_user(**kwargs):
        fields = {
            'id': str(time()),
            'first_name': 'user',
            **kwargs,
        }
        return User.objects.create(**fields)

    request.cls.create_user = staticmethod(_create_user)
    return _create_user


@pytest.fixture(scope='class')
def create_chat(request: FixtureRequest) -> Callable:
    def _create_chat(**kwargs):
        fields = {
            'id': str(time()),
            'type': TGChat.SUPERGROUP,
            **kwargs,
        }
        return Chat.objects.create(**fields)

    request.cls.create_chat = staticmethod(_create_chat)
    return _create_chat
