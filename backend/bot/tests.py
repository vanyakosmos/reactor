import pytest

from bot.consts import MAX_BUTTON_LEN
from bot.core.commands import format_chat_settings
from bot.markup import (
    make_credits_keyboard,
    merge_keyboards,
    gen_buttons,
    make_reactions_keyboard,
    make_reply_markup,
)
from bot.utils import clear_buttons
from core.models import Chat, Message, User


@pytest.mark.django_db
def test_format_chat_settings():
    chat = Chat.objects.create(id='c1', type='group')
    content = format_chat_settings(chat)
    print(content)
    assert isinstance(content, str)


class TestUtils:
    def test_clear_buttons(self):
        # test long
        bs = clear_buttons(['a', 'b', 'c' * MAX_BUTTON_LEN, 'd' * (MAX_BUTTON_LEN + 1)])
        assert bs == ['a', 'b', 'c' * MAX_BUTTON_LEN]

        # test duplicated
        bs = clear_buttons(['a', 'b', 'a', 'c'])
        assert bs == ['a', 'b', 'c']

        # emojis
        bs = clear_buttons(['a', 'b', 'c'], emojis=True)
        assert bs is None
        bs = clear_buttons(['👍', '👎'], emojis=True)
        assert bs == ['👍', '👎']


class TestMarkup:
    user = {
        'from_name': 'name',
        'from_username': 'username',
    }
    forward = {
        'forward_name': 'forward_name',
        'forward_username': 'forward_username',
    }
    forward_chat = {
        'forward_chat_name': 'chat name',
        'forward_chat_username': 'chat_username',
        'forward_chat_message_id': '1',
    }

    def test_make_credits_keyboard(self):
        # anonymous
        kb = make_credits_keyboard()
        assert kb is None

        # original post
        kb = make_credits_keyboard(**self.user).inline_keyboard
        assert len(kb) == 1  # row
        assert len(kb[0]) == 1  # col
        assert self.user['from_username'] in kb[0][0].url

        # forward from user w/o username
        kb = make_credits_keyboard(**self.user, forward_name='user').inline_keyboard
        assert len(kb) == 1  # row
        assert len(kb[0]) == 1  # col
        assert 'from' in kb[0][0].text
        assert self.user['from_username'] in kb[0][0].url

        # forward from user w/ username
        kb = make_credits_keyboard(**self.user, **self.forward).inline_keyboard
        assert len(kb) == 1  # row
        assert len(kb[0]) == 2  # col
        assert self.user['from_username'] in kb[0][0].url
        assert self.forward['forward_username'] in kb[0][1].url

        # forward from chat
        kb = make_credits_keyboard(**self.user, **self.forward_chat).inline_keyboard
        assert len(kb) == 1  # row
        assert len(kb[0]) == 2  # col
        assert self.user['from_username'] in kb[0][0].url
        assert self.forward_chat['forward_chat_username'] in kb[0][1].url
        assert self.forward_chat['forward_chat_message_id'] in kb[0][1].url

    def test_merge_keyboards(self):
        kb1 = make_credits_keyboard(**self.user)
        kb2 = make_credits_keyboard(**self.user, **self.forward)
        kb = merge_keyboards(kb1, None, kb2, None, None).inline_keyboard
        assert len(kb) == 2
        assert len(kb[0]) == 1
        assert len(kb[1]) == 2

    def test_gen_buttons(self):
        buttons = gen_buttons(['a', ('b', 2)], blank=False)
        buttons = [(b.text, b.callback_data) for b in buttons]
        assert buttons == [('a', 'button:a'), ('b 2', 'button:b')]

    def test_gen_buttons_blank(self):
        buttons = gen_buttons(['a', ('b', 2)], blank=True)
        buttons = [(b.text, b.callback_data) for b in buttons]
        assert buttons == [('a', '~'), ('b 2', '~')]

    def test_gen_buttons_big(self):
        buttons = gen_buttons([('a', 5), ('b', 20000)], blank=False)
        buttons = [(b.text, b.callback_data) for b in buttons]
        assert buttons == [('a 5', 'button:a'), ('b 20k', 'button:b')]

        buttons = gen_buttons([('a', 5), ('b', 20100)], blank=False)
        buttons = [(b.text, b.callback_data) for b in buttons]
        assert buttons == [('a 5', 'button:a'), ('b 20.1k', 'button:b')]

    def test_make_reactions_keyboard(self):
        kb = make_reactions_keyboard(['a', 'b']).inline_keyboard
        assert len(kb) == 1
        assert len(kb[0]) == 2

        kb = make_reactions_keyboard(list('abcdef'), max_cols=5).inline_keyboard
        assert len(kb) == 2
        assert [b.text for b in kb[0]] == ['a', 'b', 'c', 'd', 'e']
        assert [b.text for b in kb[1]] == ['f']

        kb = make_reactions_keyboard(list('abcdef'), max_cols=3).inline_keyboard
        assert len(kb) == 2
        assert [b.text for b in kb[0]] == ['a', 'b', 'c']
        assert [b.text for b in kb[1]] == ['d', 'e', 'f']

    def test_make_reactions_keyboard_padding(self):
        kb = make_reactions_keyboard(list('abcdef'), max_cols=5, padding=True).inline_keyboard
        assert len(kb) == 2
        assert [b.text for b in kb[0]] == ['a', 'b', 'c', 'd', 'e']
        assert [b.text for b in kb[1]] == ['f', '.', '.', '.', '.']
        assert [b.callback_data for b in kb[1][1:]] == ['~'] * 4


@pytest.mark.usefixtures(
    'create_update',
    'create_bot',
    'create_user',
    'create_chat',
    'create_message',
)
@pytest.mark.django_db
class TestMarkupWithDB:
    def make_msg_kb(self, bot, update, buttons):
        inline_id = update.chosen_inline_result.inline_message_id
        message = Message.objects.create_from_inline(
            inline_message_id=inline_id,
            from_user=User.objects.from_update(update),
            buttons=buttons,
        )
        kb = make_reply_markup(update, bot, buttons, message=message)[1].inline_keyboard
        return kb

    def test_make_reply_markup_inline(self):
        bot = self.create_bot()
        update = self.create_update(bot=bot, inline_feedback=True)
        kb = self.make_msg_kb(bot, update, buttons=['a', 'b', 'c'])
        assert len(kb) == 2
        assert kb[0][0].text == 'add reaction'
        assert len(kb[1]) == 3  # buttons

    def test_make_reply_markup_inline_wo_buttons(self):
        bot = self.create_bot()
        update = self.create_update(bot=bot, inline_feedback=True)
        kb = self.make_msg_kb(bot, update, buttons=[])
        assert len(kb) == 1
        assert kb[0][0].text == 'add reaction'

    def test_make_reply_markup_chat(self):
        bot = self.create_bot()
        user = self.create_user()
        chat = self.create_chat(buttons=['a', 'b', 'c'])
        update = self.create_update(bot=bot, user=user.tg, chat=chat.tg)

        # normal
        kb = make_reply_markup(update, bot, chat=chat, anonymous=False)[1].inline_keyboard
        assert len(kb) == 2
        assert user.first_name in kb[0][0].text
        assert len(kb[1]) == 3  # buttons

        # anonymous
        kb = make_reply_markup(update, bot, chat=chat, anonymous=True)[1].inline_keyboard
        assert len(kb) == 1
        assert [b.text for b in kb[0]] == ['a', 'b', 'c']

        # override buttons
        kb = make_reply_markup(update, bot, ['d', 'e'], chat=chat, anonymous=False)[1]
        kb = kb.inline_keyboard
        assert len(kb) == 2
        assert user.first_name in kb[0][0].text
        assert [b.text for b in kb[1]] == ['d', 'e']

        # remove buttons
        kb = make_reply_markup(update, bot, [], chat=chat, anonymous=False)[1]
        kb = kb.inline_keyboard
        assert len(kb) == 1
        assert user.first_name in kb[0][0].text

    def test_make_reply_markup_message_from_chat(self):
        bot = self.create_bot()
        user = self.create_user()
        user2 = self.create_user(first_name='user2', username='user2')  # make user linkable
        chat = self.create_chat(buttons=['1', '2', '3'])

        # normal
        message = self.create_message(buttons=['a', 'b', 'c'], chat=chat, from_user=user)
        update = self.create_update(bot=bot, message=message.tg)
        chat, kb = make_reply_markup(update, bot, message=message)
        kb = kb.inline_keyboard
        assert len(kb) == 2
        assert user.first_name in kb[0][0].text
        assert [b.text for b in kb[1]] == ['a', 'b', 'c']

        # anonymous
        message = self.create_message(
            buttons=['a', 'b', 'c'],
            chat=chat,
            anonymous=True,
            from_user=user,
        )
        update = self.create_update(bot=bot, message=message.tg)
        kb = make_reply_markup(update, bot, message=message)[1].inline_keyboard
        assert len(kb) == 1
        assert [b.text for b in kb[0]] == ['a', 'b', 'c']

        # forward
        message = self.create_message(
            buttons=['a', 'b', 'c'],
            chat=chat,
            anonymous=False,
            from_user=user,
            forward_from=user2,
        )
        update = self.create_update(bot=bot, message=message.tg)
        kb = make_reply_markup(update, bot, message=message)[1].inline_keyboard
        assert len(kb) == 2
        assert len(kb[0]) == 2
        assert [b.text for b in kb[1]] == ['a', 'b', 'c']
