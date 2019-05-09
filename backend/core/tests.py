from collections import namedtuple

import pytest

from core.models import *


@pytest.fixture
def data():
    c = Chat.objects.create(id='c1')
    m = Message.objects.create(chat_id=c.id, message_id='m1')
    k = m.keyboard
    bs = k.button_set.all()
    b1 = bs[0]
    b2 = bs[1]
    data = locals()
    return namedtuple('Data', sorted(data))(**data)


@pytest.mark.django_db
def test_remove_reaction(data):
    r = Reaction.objects.react(
        user_id='u2',
        chat_id=data.c.id,
        message_id=data.m.id,
        button_id=data.b1.pk,
    )
    assert r is not None
    assert r.button == data.b1
    assert Reaction.objects.all().count() == 1

    r = Reaction.objects.react(
        user_id='u2',
        chat_id=data.c.id,
        message_id=data.m.id,
        button_id=data.b1.pk,
    )
    assert r is None
    assert Reaction.objects.all().count() == 0


@pytest.mark.django_db
def test_change_reaction(data):
    r = Reaction.objects.react(
        user_id='u1',
        chat_id=data.c.id,
        message_id=data.m.id,
        button_id=data.b1.pk,
    )
    assert r is not None
    assert r.button == data.b1
    assert Reaction.objects.all().count() == 1

    r = Reaction.objects.react(
        user_id='u1',
        chat_id=data.c.id,
        message_id=data.m.id,
        button_id=data.b2.pk,
    )
    assert r is not None
    assert r.button == data.b2
    assert Reaction.objects.all().count() == 1


@pytest.mark.django_db
def test_reactions_count(data):
    Reaction.objects.react(
        user_id='u1',
        chat_id=data.c.id,
        message_id=data.m.id,
        button_id=data.b1.pk,
    )
    Reaction.objects.react(
        user_id='u2',
        chat_id=data.c.id,
        message_id=data.m.id,
        button_id=data.b1.pk,
    )
    Reaction.objects.react(
        user_id='u3',
        chat_id=data.c.id,
        message_id=data.m.id,
        button_id=data.b2.pk,
    )
    d = data.m.reactions()
    assert len(d) == 2
