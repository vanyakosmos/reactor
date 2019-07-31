import uuid
from typing import Callable, Union

import pytest
from _pytest.fixtures import FixtureRequest
from django.conf import settings
from django.utils import timezone
from telegram import (
    Chat as TGChat,
    User as TGUser,
    Message as TGMessage,
    Update,
    Bot,
    TelegramObject,
)

from core.models import Button, Chat, Message, User


@pytest.fixture
def mock_bot(mocker, create_tg_user):
    def get_me(bot):
        bot_user = create_tg_user(is_bot=True, first_name='bot', username='foobot')
        bot.bot = bot_user
        return bot_user

    mocker.patch.object(Bot, 'get_me', get_me)


def decode_tg_object(obj: Union[TelegramObject, dict, None, int], default=None):
    if obj is None:
        return default
    if isinstance(obj, int):
        return None
    if isinstance(obj, dict):
        return obj
    return obj.to_dict()


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
def create_message(request: FixtureRequest, create_user) -> Callable:
    def _create_message(buttons=None, **kwargs):
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
        msg = Message.objects.create(**fields)
        if buttons:
            msg.set_buttons(buttons)
        return msg

    return append_to_cls(request, _create_message)


@pytest.fixture(scope='class')
def create_tg_message(
    request: FixtureRequest, create_bot, create_tg_user, create_tg_chat
) -> Callable:
    def _create_tg_message(bot=None, user=None, chat=None, **kwargs):
        bot = bot or create_bot()
        user = decode_tg_object(user, create_tg_user().to_dict())
        chat = decode_tg_object(chat, create_tg_chat().to_dict())
        data = {
            'message_id': 1,
            'date': 1564646464,
            'from': user,
            'chat': chat,
            **kwargs,
        }
        return TGMessage.de_json(data, bot)

    return append_to_cls(request, _create_tg_message)


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


@pytest.fixture(scope='class')
def create_bot(request: FixtureRequest) -> Callable:
    def _create_bot():
        return Bot(settings.TG_BOT_TOKEN)

    return append_to_cls(request, _create_bot)


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
        inline_feedback=False,
        user: TGUser = None,
        forward_from: TGChat = None,
        chat: TGChat = None,
        message: TGMessage = None,
    ):
        bot = bot or create_bot()
        user = decode_tg_object(user, create_tg_user().to_dict())
        chat = decode_tg_object(chat, create_tg_chat().to_dict())
        message = decode_tg_object(message, create_tg_message(user=user, chat=chat).to_dict())
        if inline_feedback:
            data = {
                'update_id': 486565656,
                'chosen_inline_result': {
                    'result_id': '8f35f7c9-10f6-432c-ab16-cb9bae7f7300',
                    'query': '2a9d964c-d8b3-486a-9bb2-a98ad358dade',
                    'inline_message_id': 'AgAAAKZCAABX4ui8H4EjLpoSVZE',
                    'from': user,
                },
            }
        else:
            data = {
                'update_id': 486565656,
                'message': message,
            }

        if forward_from and 'message' in data:
            data['message']['forward_from'] = decode_tg_object(forward_from)

        return Update.de_json(data, bot)

    return append_to_cls(request, _create_update)
