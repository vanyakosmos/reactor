from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone
from telegram import Chat as TGChat, User as TGUser

from core.models import User, Chat, Message, Button, Reaction, UserButtons, MessageToPublish


@pytest.mark.usefixtures('create_user')
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

    def test_full_name(self):
        u = self.create_user(first_name='a', last_name='b')
        assert u.full_name == 'a b'
        u = self.create_user(first_name='a', username='un')
        assert u.full_name == 'un'
        u = self.create_user(first_name='a')
        assert u.full_name == 'a'

    def test_url(self):
        u = self.create_user(first_name='a', last_name='b')
        assert u.url is None
        u = self.create_user(username='username')
        assert 'username' in u.url


@pytest.mark.usefixtures('create_chat')
@pytest.mark.django_db
class TestChatModel:
    def test_create(self):
        tg_chat = TGChat(id='1111', type=TGChat.SUPERGROUP)
        Chat.objects.from_tg_chat(tg_chat)
        assert Chat.objects.filter(id=tg_chat.id).exists()

        tg_chat = TGChat(id='1111', type=TGChat.PRIVATE, first_name='a', last_name='b')
        Chat.objects.from_tg_chat(tg_chat)
        assert Chat.objects.filter(id=tg_chat.id).exists()

    def test_update(self):
        tg_chat = TGChat(id='1111', type=TGChat.SUPERGROUP)
        Chat.objects.from_tg_chat(tg_chat)

        tg_chat_2 = TGChat(id=tg_chat.id, type=TGChat.GROUP)
        Chat.objects.from_tg_chat(tg_chat_2)
        assert Chat.objects.filter(id=tg_chat.id, type=TGChat.GROUP).count() == 1

    def test_url(self):
        c = self.create_chat()
        assert c.url is None
        c = self.create_chat(username='username')
        assert 'username' in c.url


@pytest.mark.usefixtures('create_user', 'create_chat', 'create_message')
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

    def test_delete_old(self):
        past = timezone.now() - timedelta(days=30)
        self.create_message(date=past)  # 30 days old msg
        self.create_message(date=past + timedelta(days=10))  # 20 days old msg
        self.create_message(date=past + timedelta(days=20))  # 10 days old msg
        assert Message.objects.count() == 3
        r = Message.objects.delete_old(delta=timedelta(days=60))
        assert r == 0
        assert Message.objects.count() == 3

        r = Message.objects.delete_old(delta=timedelta(days=25))
        assert r == 1
        assert Message.objects.count() == 2

        r = Message.objects.delete_old(delta=timedelta(days=5))
        assert r == 2
        assert Message.objects.count() == 0

    def test_get_id(self):
        assert Message.get_id('a', 'b', 'c') == 'c'
        assert Message.get_id('a', 'b') == 'a_b'
        assert Message.get_id('a', 'b_c') == 'b_c'
        assert Message.get_id('a', None) == 'a'

    def test_split_umid(self):
        assert Message.split_id('a_b') == ['a', 'b']


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
        assert settings.MAX_NUM_BUTTONS > 1

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
        self.create_button(message=msg, text='a', index=settings.MAX_NUM_BUTTONS)
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


@pytest.mark.usefixtures(
    'create_user',
    'create_tg_user',
    'create_message',
    'create_button',
    'create_chat',
)
@pytest.mark.django_db
class TestReactionModel:
    def test_safe_create_with_user(self):
        user: User = self.create_user()
        msg: Message = self.create_message()
        b: Button = self.create_button()
        r = Reaction.objects.safe_create(user.tg, msg.id, b)
        assert r.user == user and r.message == msg

    @pytest.mark.django_db(transaction=True)
    def test_safe_create_without_user(self):
        msg: Message = self.create_message()
        b: Button = self.create_button()
        tg_user = TGUser(id='111', first_name='user', is_bot=False)
        r = Reaction.objects.safe_create(tg_user, msg.id, b)
        user = User.objects.get(id=tg_user.id)
        assert r.user == user and r.message == msg

    def test_react_same_button(self):
        user = self.create_user()
        msg = self.create_message(buttons=['a', 'b'])
        r1, b1 = Reaction.objects.react(user.tg, **msg.ids, button_text='a')
        assert b1.count == 1
        assert r1 is not None

        r2, b2 = Reaction.objects.react(user.tg, **msg.ids, button_text='a')
        assert b2.count == 0
        assert r2 is None

    def test_react_another_button(self):
        user = self.create_user()
        msg = self.create_message(buttons=['a', 'b'])
        r1, b1 = Reaction.objects.react(user.tg, **msg.ids, button_text='a')
        assert b1.count == 1
        assert r1 is not None

        r1, r2 = Reaction.objects.react(user.tg, **msg.ids, button_text='b')
        assert r2.count == 1
        assert r2 is not None

        b1.refresh_from_db()
        assert b1.count == 0

    @pytest.mark.django_db(transaction=True)
    def test_react_new_user(self):
        tg_user = self.create_tg_user()
        msg = self.create_message(buttons=['a', 'b'])
        r1, b1 = Reaction.objects.react(tg_user, **msg.ids, button_text='a')
        assert b1.count == 1
        assert r1 is not None
        assert User.objects.filter(id=tg_user.id).exists()

    def test_react_many_users(self):
        u1 = self.create_user()
        u2 = self.create_user()
        u3 = self.create_user()
        msg = self.create_message(buttons=['a', 'b'])
        Reaction.objects.react(u1.tg, **msg.ids, button_text='a')
        Reaction.objects.react(u2.tg, **msg.ids, button_text='a')
        Reaction.objects.react(u3.tg, **msg.ids, button_text='b')
        buttons = Button.objects.values_list('text', 'count').order_by('index')
        assert list(buttons) == [('a', 2), ('b', 1)]
        assert Reaction.objects.count() == 3

    def test_react_too_many(self):
        user = self.create_user()
        msg = self.create_message(buttons=list(map(str, range(settings.MAX_NUM_BUTTONS))))
        r1, b1 = Reaction.objects.react(user.tg, **msg.ids, button_text='a')
        assert b1 is None
        assert r1 is None


@pytest.mark.usefixtures('create_user')
@pytest.mark.django_db
class TestUserButtonsModel:
    def test_create_two(self):
        user = self.create_user()
        UserButtons.create(user.id, ['a', 'b'])
        assert UserButtons.objects.count() == 1
        UserButtons.create(user.id, ['a', 'c'])
        assert UserButtons.objects.count() == 2

    def test_create_same(self):
        user = self.create_user()
        UserButtons.create(user.id, ['a', 'b'])
        assert UserButtons.objects.count() == 1
        UserButtons.create(user.id, ['a', 'b'])
        assert UserButtons.objects.count() == 1

    def test_create_too_many(self):
        user = self.create_user()
        mub = settings.MAX_USER_BUTTONS_HINTS
        for i in range(mub):
            UserButtons.create(user.id, [str(i)])
            assert UserButtons.objects.count() == i + 1

        assert UserButtons.objects.count() == mub
        UserButtons.create(user.id, ['new'])
        assert UserButtons.objects.count() == mub
        assert UserButtons.objects.filter(user=user, buttons__exact=['new']).exists()

    def test_buttons_list(self):
        user = self.create_user()
        UserButtons.create(user.id, ['a', 'b'])
        UserButtons.create(user.id, ['c', 'd'])

        # -created order
        assert UserButtons.buttons_list(user.id) == ['c d', 'a b']


@pytest.mark.usefixtures('create_user')
@pytest.mark.django_db
class TestMessageToPublishModel:
    def test_delete_old(self, mocker):
        user = self.create_user()
        now = timezone.now  # stash now
        past = timezone.now() - timedelta(days=30)
        mocker.patch('django.utils.timezone.now', lambda: past)
        MessageToPublish.objects.create(user=user, message={})
        mocker.patch('django.utils.timezone.now', lambda: past + timedelta(days=10))
        MessageToPublish.objects.create(user=user, message={})
        mocker.patch('django.utils.timezone.now', lambda: past + timedelta(days=20))
        MessageToPublish.objects.create(user=user, message={})

        # restore now
        mocker.patch('django.utils.timezone.now', now)

        assert MessageToPublish.objects.count() == 3

        r = MessageToPublish.objects.delete_old(delta=timedelta(days=60))
        assert r == 0
        assert MessageToPublish.objects.count() == 3

        r = MessageToPublish.objects.delete_old(delta=timedelta(days=25))
        assert r == 1
        assert MessageToPublish.objects.count() == 2

        r = MessageToPublish.objects.delete_old(delta=timedelta(days=5))
        assert r == 2
        assert MessageToPublish.objects.count() == 0
