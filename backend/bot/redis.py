import json
import logging
from enum import Enum, auto

import redis
from django.conf import settings

logger = logging.getLogger(__name__)
rc = redis.Redis.from_url(settings.REDIS_URL)

STATE_EXPIRY = 60 * 60


class State(Enum):
    reaction = auto()
    create_start = auto()
    create_buttons = auto()
    create_end = auto()

    def __str__(self):
        return self._name_


def save_media_group(media_group, expire=60):
    """Save media_group to redis storage and return True if it didn't exist yet."""
    key = f'media_group:{media_group}'
    if rc.exists(key):
        return False
    rc.set(key, 1, ex=expire)
    return True


def _state_key(user):
    user = getattr(user, 'id', user)
    return f'state:{user}'


def set_state(user, state: State):
    key = _state_key(user)
    rc.hset(key, 'state', str(state))
    rc.expire(key, STATE_EXPIRY)


def set_key(user, key, value):
    state_key = _state_key(user)
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value)
    rc.hset(state_key, key, value)
    rc.expire(state_key, STATE_EXPIRY)


def get_key(user, key, default=None):
    state_key = _state_key(user)
    value = rc.hget(state_key, key)
    if not value:
        return default
    return value.decode()


def get_json(user, key, default=None):
    state_key = _state_key(user)
    value = rc.hget(state_key, key)
    if not value:
        return default
    return json.loads(value.decode())


def check_state(user, state: State):
    key = _state_key(user)
    stored_state = rc.hget(key, 'state')
    return bool(stored_state and stored_state.decode() == str(state))


def clear_state(user):
    key = _state_key(user)
    return rc.hdel(key, 'state')
