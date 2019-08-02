from collections import defaultdict
from datetime import timedelta
from random import randint

import pytest
from django.test import override_settings

from stats.models import PopularReactions, TopPosters


@pytest.mark.django_db
@pytest.mark.usefixtures('create_chat', 'create_message', 'create_button')
class TestPopularReactions:
    def test_calculate(self):
        chat = self.create_chat()
        for _ in range(randint(5, 20)):
            msg = self.create_message(chat=chat)
            for i in range(randint(1, 4)):
                self.create_button(message=msg, text=str(i), count=randint(0, 10))

        dull = defaultdict(int)
        for msg in chat.message_set.all():
            for b in msg.button_set.all():
                dull[b.text] += b.count

        pr = PopularReactions.objects.create(chat=chat)
        for r in pr.calculate():
            assert dull[r.text] == r.count

    def test_get_new(self):
        chat = self.create_chat()
        assert PopularReactions.objects.count() == 0
        PopularReactions.get(chat)
        assert PopularReactions.objects.count() == 1

    def test_expired(self):
        chat = self.create_chat()
        pr = PopularReactions.objects.create(chat=chat)
        with override_settings(STATS_EXPIRATION_DELTA=-timedelta(seconds=60)):
            assert pr.expired
        with override_settings(STATS_EXPIRATION_DELTA=timedelta(seconds=60)):
            assert not pr.expired


@pytest.mark.django_db
@pytest.mark.usefixtures('create_chat', 'create_message', 'create_button', 'create_user')
class TestTopPosters:
    def test_calculate(self):
        chat = self.create_chat()

        users = [self.create_user() for _ in range(randint(2, 4))]
        for user in users:
            for _ in range(randint(5, 10)):
                msg = self.create_message(chat=chat, from_user=user)
                for i in range(randint(1, 4)):
                    self.create_button(message=msg, text=str(i), count=randint(0, 10))

        real = defaultdict(lambda: defaultdict(int))
        for msg in chat.message_set.all():
            real[msg.from_user.id]['messages'] += 1

        for msg in chat.message_set.all():
            for btn in msg.button_set.all():
                real[msg.from_user.id]['reactions'] += btn.count

        tp = TopPosters.objects.create(chat=chat)
        for poster in tp.calculate():
            v = real[poster.user_id]
            assert v['messages'] == poster.messages
            assert v['reactions'] == poster.reactions

    def test_get_new(self):
        chat = self.create_chat()
        assert TopPosters.objects.count() == 0
        TopPosters.get(chat)
        assert TopPosters.objects.count() == 1

    def test_expired(self):
        chat = self.create_chat()
        pr = TopPosters.objects.create(chat=chat)
        with override_settings(STATS_EXPIRATION_DELTA=-timedelta(seconds=60)):
            assert pr.expired
        with override_settings(STATS_EXPIRATION_DELTA=timedelta(seconds=60)):
            assert not pr.expired
