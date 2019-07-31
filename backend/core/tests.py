import pytest
from django.utils import timezone
from telegram import Chat as TGChat, Message as TGMessage, User as TGUser

from bot.consts import MAX_NUM_BUTTONS
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


@pytest.mark.usefixtures('create_chat', 'create_message', 'create_button')
@pytest.mark.django_db
class TestButtonModel:
    def test_inc(self):
        b = self.create_button()
        assert b.count == 0
        b.inc()
        assert b.count == 1

    def test_dec(self):
        b = self.create_button(count=2)
        assert b.count == 2
        b.dec()
        assert b.count == 1
        b.dec()
        with pytest.raises(Button.DoesNotExist):
            b.refresh_from_db()

    def test_dec_permanent(self):
        b = self.create_button(count=2, permanent=True)
        assert b.count == 2
        b.dec()
        assert b.count == 1
        b.dec()
        assert b.count == 0
        b.dec()
        assert b.count == 0

    def test_get_for_reaction(self):
        assert MAX_NUM_BUTTONS > 1

        msg = self.create_message()
        # create and get the same button twice
        b0 = Button.objects.get_for_reaction('a', msg.id)
        b1 = Button.objects.get_for_reaction('a', msg.id)
        assert b0 == b1
        assert b1.index == 0 and b1.text == 'a'

        # create next button
        b2 = Button.objects.get_for_reaction('b', msg.id)
        assert b2.index == 1 and b2.text == 'b'

    def test_get_for_reaction_of_limit(self):
        msg = self.create_message()
        self.create_button(message=msg, text='a', index=MAX_NUM_BUTTONS)
        b1 = Button.objects.get_for_reaction('b', msg.id)
        assert b1 is None

    def test_no_reactions(self):
        msg: Message = self.create_message()
        reactions = Button.objects.reactions(**msg.ids)
        assert len(reactions) == 0

    def test_reactions_inline_msg(self):
        msg: Message = self.create_message()
        self.create_button(message=msg, text='a', index=1)
        self.create_button(message=msg, text='b', index=0, count=5)
        reactions = Button.objects.reactions(**msg.ids)
        # sorted by index
        assert reactions == [('b', 5), ('a', 0)]

    def test_reactions(self):
        chat = self.create_chat()
        msg: Message = self.create_message(chat=chat)
        self.create_button(message=msg, text='a', count=10)
        reactions = Button.objects.reactions(**msg.ids)
        assert reactions == [('a', 10)]
