import pytest
from django.utils import timezone
from telegram import Chat as TGChat, Message as TGMessage, User as TGUser

from core.models import *


@pytest.mark.django_db
class TestUserModel:
    def test_create(self):
        tg_user = TGUser(id='1111', first_name='user', is_bot=False)
        User.objects.from_tg_user(tg_user)
        assert User.objects.filter(id=tg_user.id, first_name=tg_user.first_name).count() == 1

    def test_update(self):
        tg_user = TGUser(id='1111', first_name='user', is_bot=False)
        User.objects.from_tg_user(tg_user)

        tg_user_2 = TGUser(id=tg_user.id, first_name='user 2', is_bot=False)
        User.objects.from_tg_user(tg_user_2)
        assert User.objects.filter(id=tg_user_2.id, first_name=tg_user_2.first_name).count() == 1


@pytest.mark.django_db
class TestChatModel:
    def test_create(self):
        tg_chat = TGChat(id='1111', type=TGChat.SUPERGROUP)
        Chat.objects.from_tg_chat(tg_chat)
        assert Chat.objects.filter(id=tg_chat.id).count() == 1

    def test_update(self):
        tg_chat = TGChat(id='1111', type=TGChat.SUPERGROUP)
        Chat.objects.from_tg_chat(tg_chat)

        tg_chat_2 = TGChat(id=tg_chat.id, type=TGChat.GROUP)
        Chat.objects.from_tg_chat(tg_chat_2)
        assert Chat.objects.filter(id=tg_chat.id, type=TGChat.GROUP).count() == 1


@pytest.mark.usefixtures('create_user', 'create_chat')
@pytest.mark.django_db
class TestMessageModel:
    def test_get_by_id(self):
        user = self.create_user()

        msg = Message.objects.create(id='1111', date=timezone.now(), from_user=user)
        m = Message.objects.get_by_ids(None, None, '1111')
        assert m == msg

        msg = Message.objects.create(id='1111_2222', date=timezone.now(), from_user=user)
        m = Message.objects.get_by_ids('1111', '2222')
        assert m == msg

    def test_create_inline(self):
        user = self.create_user()
        msg = Message.objects.create_from_inline('1111', user, [])
        assert msg.is_inline

    def test_create_from_tg(self):
        user = self.create_user()
        chat = self.create_chat()
        msg = Message.objects.create_from_tg_ids(chat.id, '2222', timezone.now(), user)
        assert chat == msg.chat
        assert msg.id == f'{chat.id}_2222'
