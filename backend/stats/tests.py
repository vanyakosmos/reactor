from collections import defaultdict
from datetime import timedelta
from random import randint

import pytest
from django.test import override_settings
from django.utils import timezone

from stats.models import PopularReactions


@pytest.mark.django_db
@pytest.mark.usefixtures('create_chat', 'create_message', 'create_button')
class TestPopularReactions:
    def test_calculate(self):
        chat = self.create_chat()
        for _ in range(20):
            msg = self.create_message(chat=chat)
            for i in range(randint(1, 4)):
                text = str(i)
                count = randint(0, 10)
                self.create_button(message=msg, text=text, count=count)

        dull = defaultdict(lambda: 0)
        for msg in chat.message_set.all():
            for b in msg.button_set.all():
                dull[b.text] += b.count

        pr = PopularReactions.objects.create(chat=chat, updated=timezone.now())
        for r in pr.calculate():
            assert dull[r.text] == r.count

    def test_get_new(self):
        chat = self.create_chat()
        assert PopularReactions.objects.count() == 0
        PopularReactions.get(chat)
        assert PopularReactions.objects.count() == 1

    def test_expired(self):
        chat = self.create_chat()
        pr = PopularReactions.objects.create(chat=chat, updated=timezone.now())
        with override_settings(STATS_EXPIRATION_DELTA=-timedelta(seconds=60)):
            assert pr.expired
        with override_settings(STATS_EXPIRATION_DELTA=timedelta(seconds=60)):
            assert not pr.expired
