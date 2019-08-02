import pytest
from telegram import Bot

from bot import redis


@pytest.fixture
def mock_bot(mocker, create_tg_user):
    def get_me(bot):
        bot_user = create_tg_user(is_bot=True, first_name='bot', username='foobot')
        bot.bot = bot_user
        return bot_user

    def bot_is_admin(*args, **kwargs):
        return True

    bot_mocks = [
        ('get_me', get_me),
        'send_message',
        'answer_inline_query',
        'answer_callback_query',
        'answerCallbackQuery',
        'edit_message_reply_markup',
        'send_chat_action',
        'delete_message',
    ]
    for mock in bot_mocks:
        if isinstance(mock, str):
            mock = (mock,)
        mocker.patch.object(Bot, *mock)

    mocker.patch('bot.utils.bot_is_admin', bot_is_admin)


@pytest.fixture
def mock_redis(mocker):
    mocker.patch.object(redis, 'rc')
