from collections import defaultdict
from datetime import timedelta
from random import randint

import pytest
from django.test import override_settings

from core.models import User
from stats.models import PopularReactions, TopPosters, Reaction, Poster


# noinspection PyUnresolvedReferences
class SetupMixin:
    def setup_chat(self):
        chat = self.create_chat()
        users = [self.create_user() for _ in range(randint(2, 4))]
        for user in users:
            for _ in range(randint(5, 10)):
                anon = randint(0, 100) > 70
                msg = self.create_message(chat=chat, from_user=user, anonymous=anon)
                for i in range(randint(1, 4)):
                    self.create_button(message=msg, text=str(i), count=randint(0, 10))
        return chat


@pytest.mark.django_db
@pytest.mark.usefixtures('create_chat', 'create_message', 'create_button')
class TestPopularReactions(SetupMixin):
    def test_calculate(self):
        chat = self.setup_chat()

        dull = defaultdict(int)
        for msg in chat.message_set.all():
            for b in msg.button_set.all():
                dull[b.text] += b.count

        pr = PopularReactions.objects.create(chat=chat)
        for r in pr.calculate():
            assert dull[r.text] == r.count

    def test_get_new(self):
        chat = self.setup_chat()
        assert PopularReactions.objects.count() == 0
        assert Reaction.objects.count() == 0
        PopularReactions.get(chat)
        assert PopularReactions.objects.count() == 1
        assert Reaction.objects.count() == Reaction.objects.count() > 0

    def test_expired(self):
        chat = self.create_chat()
        pr = PopularReactions.objects.create(chat=chat)
        with override_settings(STATS_EXPIRATION_DELTA=-timedelta(seconds=60)):
            assert pr.expired
        with override_settings(STATS_EXPIRATION_DELTA=timedelta(seconds=60)):
            assert not pr.expired


@pytest.mark.django_db
@pytest.mark.usefixtures('create_chat', 'create_message', 'create_button', 'create_user')
class TestTopPosters(SetupMixin):
    def test_calculate(self):
        chat = self.setup_chat()

        real = defaultdict(lambda: defaultdict(int))
        for msg in chat.message_set.filter(anonymous=False):
            real[msg.from_user.id]['messages'] += 1

        for msg in chat.message_set.filter(anonymous=False):
            for btn in msg.button_set.all():
                real[msg.from_user.id]['reactions'] += btn.count

        tp = TopPosters.objects.create(chat=chat)
        for poster in tp.calculate():
            v = real[poster.user_id]
            assert v['messages'] == poster.messages
            assert v['reactions'] == poster.reactions

    def test_get_new(self):
        chat = self.setup_chat()
        assert TopPosters.objects.count() == 0
        assert Poster.objects.count() == 0
        TopPosters.get(chat)
        assert TopPosters.objects.count() == 1
        assert Poster.objects.count() == User.objects.count() > 0

    def test_expired(self):
        chat = self.create_chat()
        pr = TopPosters.objects.create(chat=chat)
        with override_settings(STATS_EXPIRATION_DELTA=-timedelta(seconds=60)):
            assert pr.expired
        with override_settings(STATS_EXPIRATION_DELTA=timedelta(seconds=60)):
            assert not pr.expired
