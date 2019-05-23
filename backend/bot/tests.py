import pytest

from bot.handlers.commands import format_chat_settings
from core.models import Chat


@pytest.mark.django_db
def test_format_chat_settings():
    chat = Chat.objects.create(id='c1', type='group')
    content = format_chat_settings(chat)
    print(content)
    assert isinstance(content, str)
