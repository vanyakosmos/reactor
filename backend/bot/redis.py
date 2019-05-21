import json
import logging
from typing import Tuple

import redis
from django.conf import settings
from telegram import Message as TGMessage

logger = logging.getLogger(__name__)
rc = redis.Redis.from_url(settings.REDIS_URL)

AWAITING_REACTION = 'AWAITING_REACTION'
AWAITING_CREATION = 'AWAITING_CREATION'


def save_media_group(media_group, expire=60):
    """Save media_group to redis storage and return True if it didn't exist yet."""
    key = f'media_group:{media_group}'
    if rc.exists(key):
        return False
    rc.set(key, 1, ex=expire)
    return True


def _state_key(user):
    return f'state:{user}'


def _set_state(user, state, payload=None, expire=60 * 60):
    logger.debug(f"set state: {user}, {state}, {payload}")
    key = _state_key(user)
    rc.hset(key, 'state', state)
    if payload:
        rc.hset(key, 'payload', payload)
    rc.expire(key, expire)


def _del_state(user, state):
    key = _state_key(user)
    s = rc.hget(key, 'state')
    if s and s.decode() == state:
        return rc.delete(key)


def await_reaction(user, payload):
    _set_state(user, AWAITING_REACTION, payload)


def awaited_reaction(user):
    key = _state_key(user)
    state = rc.hget(key, 'state')
    if state and state.decode() == AWAITING_REACTION:
        return rc.hget(key, 'payload')


def stop_awaiting_reaction(user):
    _del_state(user, AWAITING_REACTION)


def await_create(user):
    _set_state(user, AWAITING_CREATION)


def awaiting_creation(user):
    key = _state_key(user)
    state = rc.hget(key, 'state')
    return state and state.decode() == AWAITING_CREATION


def save_creation(user, message_dict, buttons, expire=60 * 60):
    key = _state_key(user)
    rc.hset(key, 'state', AWAITING_CREATION)
    rc.hset(key, 'message', json.dumps(message_dict))
    rc.hset(key, 'buttons', json.dumps(buttons))
    rc.expire(key, expire)


def get_creation(user, bot) -> Tuple[TGMessage, list]:
    key = _state_key(user)
    message = json.loads(rc.hget(key, 'message'))
    message = TGMessage.de_json(message, bot)
    buttons = json.loads(rc.hget(key, 'buttons'))
    return message, buttons


def stop_awaiting_creation(user):
    _del_state(user, AWAITING_CREATION)
