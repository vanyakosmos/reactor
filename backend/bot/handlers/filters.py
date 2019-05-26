from telegram import Message as TGMessage, User as TGUser
from telegram.ext import BaseFilter

from bot import redis
from bot.redis import State


class ReplyToBot(BaseFilter):
    def filter(self, message: TGMessage):
        return (
            message.reply_to_message and
            message.bot.username == message.reply_to_message.from_user.username
        )


reply_to_bot = ReplyToBot()


class StateFilter:
    class _StateFilter(BaseFilter):
        def __init__(self, state):
            self.state = state
            self.name = f'StateFilter({state})'

        def filter_by_user(self, user: TGUser):
            return bool(user and redis.check_state(user.id, self.state))

        def filter(self, message: TGMessage):
            user: TGUser = message.from_user
            return self.filter_by_user(user)

    reaction = _StateFilter(State.reaction)
    create_start = _StateFilter(State.create_start)
    create_buttons = _StateFilter(State.create_buttons)
    create_end = _StateFilter(State.create_end)
