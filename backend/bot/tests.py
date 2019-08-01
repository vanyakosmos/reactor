import pytest
from telegram import Bot

from bot.channel_publishing import command_create, handle_publishing_options, handle_publishing, \
    handle_create_start, handle_create_buttons
from bot.channel_reaction import command_start, handle_reaction_response
from bot.consts import MAX_BUTTON_LEN
from bot.core.commands import format_chat_settings
from bot.group_reaction import handle_reaction_reply, handle_magic_reply
from bot.magic_marks import clear_magic_marks, get_magic_marks, process_magic_mark, restore_text
from bot.markup import (
    gen_buttons,
    make_credits_keyboard,
    make_reactions_keyboard,
    make_reply_markup,
    merge_keyboards,
)
from bot import redis
from bot.utils import clear_buttons
from core.models import Chat, Message, User, MessageToPublish, Button


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

    def test_merge_keyboards_vertical_limit(self):
        kb = merge_keyboards(
            make_credits_keyboard(**self.user),
            make_reactions_keyboard(['1', '2'], padding=2),
        )
        markup = merge_keyboards(kb, kb, kb, kb, kb).inline_keyboard
        assert len(markup) == 10

        markup = merge_keyboards(kb, kb, kb, kb, kb, kb).inline_keyboard
        assert len(markup) == 10

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
    'mock_bot',
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
        update = self.create_update(bot=bot, chosen_inline_result=True)
        kb = self.make_msg_kb(bot, update, buttons=['a', 'b', 'c'])
        assert len(kb) == 2
        assert kb[0][0].text == 'add reaction'
        assert len(kb[1]) == 3  # buttons

    def test_make_reply_markup_inline_wo_buttons(self):
        bot = self.create_bot()
        update = self.create_update(bot=bot, chosen_inline_result=True)
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


@pytest.mark.usefixtures('create_tg_message')
class TestMagicMarks:
    def test_get_magic_marks_bad_text(self):
        ms = get_magic_marks('')
        assert ms is None

        ms = get_magic_marks('foo')
        assert ms is None

        ms = get_magic_marks('.foo')
        assert ms is None

        ms = get_magic_marks('.foo+~``')
        assert ms is None

    def test_get_magic_marks(self):
        ms = get_magic_marks('.+')
        assert ms == ['+']

        ms = get_magic_marks('.~')
        assert ms == ['~']

        ms = get_magic_marks('.`a b`')
        assert ms == ['`a b`']

    def test_get_magic_marks_multiple(self):
        ms = get_magic_marks('.+~`a b c`')
        assert ms == ['+', '~', '`a b c`']

    def test_clear_magic_marks(self):
        text = clear_magic_marks('.+', ['+'])
        assert text is None

        text = clear_magic_marks('.+foo', ['+'])
        assert text == 'foo'

        text = clear_magic_marks('.+foo~', ['+'])
        assert text == 'foo~'

        text = clear_magic_marks('.+~foo', ['+', '~'])
        assert text == 'foo'

        text = clear_magic_marks('.+~`a b`foo', ['+', '~', '`a b`'])
        assert text == 'foo'

    def test_restore_text(self):
        msg = self.create_tg_message(text='.+foo')
        assert restore_text(msg, 'foo')

        msg = self.create_tg_message(text='.+')
        assert not restore_text(msg, None)

        msg = self.create_tg_message(caption='.+foo')
        assert restore_text(msg, 'foo')

        msg = self.create_tg_message(caption='.+')
        assert restore_text(msg, None)

    def process(self, **kwargs):
        msg = self.create_tg_message(**kwargs)
        return process_magic_mark(msg)

    def test_process_magic_mark(self):
        # message might have needed media type
        force, anon, skip, buttons = self.process(text='foo')
        assert not skip

        force, anon, skip, buttons = self.process(caption='.+foo')
        assert not skip

        force, anon, skip, buttons = self.process(text='.foo')
        assert not skip

        force, anon, skip, buttons = self.process(text='.foo+')
        assert not skip

        # can't repost empty message
        force, anon, skip, buttons = self.process(text='.+`a b`')
        assert skip

        force, anon, skip, buttons = self.process(text='.-foo')
        assert skip

        force, anon, skip, buttons = self.process(text='.~foo')
        assert anon

        force, anon, skip, buttons = self.process(text='.+foo')
        assert force == 1

        force, anon, skip, buttons = self.process(text='.++foo')
        assert force == 2

        force, anon, skip, buttons = self.process(text='.``foo')
        assert buttons == []

        force, anon, skip, buttons = self.process(text='.`a b`foo')
        assert buttons == ['a', 'b']

        force, anon, skip, buttons = self.process(text='.+~++`a`foo')
        assert not skip
        assert anon
        assert force == 3
        assert buttons == ['a']

        force, anon, skip, buttons = self.process(text='.+`a`foo')
        assert not skip
        assert not anon
        assert force == 1
        assert buttons == ['a']


@pytest.fixture
def mock_get_msg_and_buttons(mocker, create_tg_message):
    def get_msg_and_buttons(*args, **kwargs):
        msg = create_tg_message(text='text')
        return msg, ['1', '2']

    mocker.patch('bot.channel_publishing.inline_handlers.get_msg_and_buttons', get_msg_and_buttons)


@pytest.mark.django_db
@pytest.mark.usefixtures(
    'mock_bot',
    'mock_redis',
    'create_bot',
    'create_update',
    'create_context',
    'create_tg_message',
    'create_user',
)
class TestChannelPublishing:
    def test_command_create(self, mocker):
        msg = self.create_tg_message(text='/create')
        update = self.create_update(message=msg)
        mocker.spy(Bot, 'send_message')
        mocker.spy(redis, 'set_state')

        command_create(update, self.create_context())

        assert Bot.send_message.call_count == 1
        assert redis.set_state.call_args[0][1] == redis.State.create_start

    def test_handle_create_start(self, mocker):
        user = self.create_user()
        msg = self.create_tg_message(text='text', user=user.tg)
        update = self.create_update(message=msg, user=user.tg)
        mocker.spy(Bot, 'send_message')
        mocker.spy(redis, 'set_state')
        assert MessageToPublish.objects.count() == 0

        handle_create_start(update, self.create_context())

        assert MessageToPublish.objects.count() == 1
        assert Bot.send_message.call_count == 1
        assert redis.set_state.call_args[0][1] == redis.State.create_buttons

    def test_handle_create_buttons_bad(self, mocker):
        user = self.create_user()
        msg = self.create_tg_message(user=user.tg, text='1 2')
        update = self.create_update(message=msg, user=user.tg)
        mtp = MessageToPublish.objects.create(
            user=user,
            message=self.create_tg_message(text='text').to_dict(),
        )
        mocker.spy(Bot, 'send_message')
        mocker.spy(redis, 'set_state')

        handle_create_buttons(update, self.create_context())

        mtp.refresh_from_db()
        assert mtp.buttons is None
        assert Bot.send_message.call_count == 1
        assert redis.set_state.call_count == 0

    def test_handle_create_buttons(self, mocker):
        user = self.create_user()
        msg = self.create_tg_message(user=user.tg, text='👍 👎')
        update = self.create_update(message=msg)
        mtp = MessageToPublish.objects.create(
            user=user,
            message=self.create_tg_message(text='text').to_dict(),
        )
        mocker.spy(Bot, 'send_message')
        mocker.spy(redis, 'set_state')

        handle_create_buttons(update, self.create_context())

        mtp.refresh_from_db()
        assert mtp.buttons == ['👍', '👎']
        assert Bot.send_message.call_count == 2
        assert redis.set_state.call_count == 1
        assert redis.set_state.call_args[0][1] == redis.State.create_end

    @pytest.mark.usefixtures('mock_get_msg_and_buttons')
    def test_handle_publishing_options(self, mocker):
        update = self.create_update(inline_query=True)
        mocker.spy(Bot, 'answer_inline_query')
        handle_publishing_options(update, self.create_context())
        assert Bot.answer_inline_query.call_count == 1

    @pytest.mark.usefixtures('mock_get_msg_and_buttons')
    def test_handle_publishing(self, mocker):
        update = self.create_update(chosen_inline_result=True)
        mocker.spy(Bot, 'edit_message_reply_markup')
        handle_publishing(update, self.create_context())
        assert Bot.edit_message_reply_markup.call_count == 1


@pytest.mark.django_db
@pytest.mark.usefixtures(
    'mock_bot',
    'mock_redis',
    'create_update',
    'create_context',
    'create_message',
    'create_user',
)
class TestChannelReaction:
    def test_command_start(self, mocker):
        self.create_message(id='1111')  # message with reactions
        msg = self.create_tg_message(text='/start 1111')
        update = self.create_update(message=msg)
        context = self.create_context(args=['1111'])
        mocker.spy(Bot, 'send_message')
        mocker.spy(redis, 'set_state')
        mocker.spy(redis, 'set_key')

        command_start(update, context)

        assert Bot.send_message.call_count == 1
        assert redis.set_state.call_args[0][1] == redis.State.reaction
        assert redis.set_key.call_args[0][1] == 'message_id'

    def test_command_start_invalid_message(self, mocker):
        self.create_message(id='2222')  # message with reactions
        msg = self.create_tg_message(text='/start 1111')
        update = self.create_update(message=msg)
        context = self.create_context(args=['1111'])  # invalid id
        mocker.spy(Bot, 'send_message')
        mocker.spy(redis, 'set_state')
        mocker.spy(redis, 'set_key')

        command_start(update, context)

        assert Bot.send_message.call_count == 1
        assert redis.set_state.call_count == 0
        assert redis.set_key.call_count == 0

    def test_handle_reaction_response_not_emoji(self, mocker):
        self.create_message(id='1111')
        msg = self.create_tg_message(text='1')
        update = self.create_update(message=msg)
        context = self.create_context()
        mocker.spy(Bot, 'send_message')
        mocker.spy(redis, 'get_key')

        assert Button.objects.count() == 0

        handle_reaction_response(update, context)

        assert Bot.send_message.call_count == 1
        assert redis.get_key.call_count == 0
        assert Button.objects.count() == 0

    def test_handle_reaction_response(self, mocker):
        user = self.create_user()
        self.create_message(id='1111', from_user=user)  # message w/ buttons
        msg = self.create_tg_message(text='👍', user=user.tg)  # reaction
        update = self.create_update(message=msg)
        context = self.create_context()
        mocker.spy(Bot, 'send_message')
        mocker.patch.object(redis, 'get_key').return_value = '1111'

        assert Button.objects.count() == 0

        handle_reaction_response(update, context)

        assert Bot.send_message.call_count == 1
        assert Button.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.usefixtures(
    'mock_bot',
    'mock_redis',
    'create_update',
    'create_context',
    'create_message',
    'create_chat',
    'create_user',
    'create_tg_message',
)
class TestGroupReaction:
    def test_reply(self):
        user = self.create_user()
        chat = self.create_chat()
        msg = self.create_message(chat=chat, from_user=user, buttons=['a', 'b'])

        reply = self.create_tg_message(user=user.tg, text='+c')
        update = self.create_update(message=reply, reply_to_message=msg.tg)
        context = self.create_context(match=['+c', 'c'])

        handle_reaction_reply(update, context)

        bs = msg.button_set.values_list('text', flat=True)
        assert list(bs) == ['a', 'b', 'c']

    def test_reply_restricted(self):
        user = self.create_user()
        chat = self.create_chat(allow_reactions=False)
        msg = self.create_message(chat=chat, from_user=user, buttons=['a', 'b'])

        reply = self.create_tg_message(user=user.tg, text='+c')
        update = self.create_update(message=reply, reply_to_message=msg.tg)
        context = self.create_context(match=['+c', 'c'])

        handle_reaction_reply(update, context)
        assert msg.button_set.count() == 2

        chat.allow_reactions = True
        chat.force_emojis = True
        chat.save()

        handle_reaction_reply(update, context)
        assert msg.button_set.count() == 2

    def test_magic_reply_buttons(self):
        user = self.create_user()
        chat = self.create_chat()
        msg = self.create_message(chat=chat, from_user=user, buttons=['a', 'b'])

        reply = self.create_tg_message(user=user.tg, text='.`c`')
        update = self.create_update(message=reply, reply_to_message=msg.tg)
        context = self.create_context()

        assert msg.button_set.count() == 2

        handle_magic_reply(update, context)

        assert msg.button_set.count() == 1

    def test_magic_reply_anon(self):
        user = self.create_user()
        chat = self.create_chat()
        msg = self.create_message(chat=chat, from_user=user, buttons=['a', 'b'])

        reply = self.create_tg_message(user=user.tg, text='.~')
        update = self.create_update(message=reply, reply_to_message=msg.tg)
        context = self.create_context()

        assert not msg.anonymous

        handle_magic_reply(update, context)

        msg.refresh_from_db()
        assert msg.anonymous
