from telegram import Message as TGMessage, User as TGUser
from telegram.ext import BaseFilter

from bot import redis


class _ReactionFilter(BaseFilter):
    def filter(self, message: TGMessage):
        user: TGUser = message.from_user
        return user and bool(redis.awaited_reaction(user.id))


reaction_filter = _ReactionFilter()


class _CreationFilter(BaseFilter):
    def filter_by_user(self, user: TGUser):
        return user and bool(redis.awaiting_creation(user.id))

    def filter(self, message: TGMessage):
        user: TGUser = message.from_user
        return self.filter_by_user(user)


creation_filter = _CreationFilter()
