import uuid
from typing import Union

from _pytest.fixtures import FixtureRequest
from telegram import TelegramObject


def append_to_cls(request: FixtureRequest, func, name=None):
    name = name or func.__name__.strip('_')
    if request.cls:
        setattr(request.cls, name, staticmethod(func))
    return func


def get_id():
    # generate 128 bit number and shift it by 64
    return str(uuid.uuid1().int >> 64)


def decode_tg_object(obj: Union[TelegramObject, dict, None, int], default=None):
    if obj is None:
        return default
    if isinstance(obj, int):
        return None
    if isinstance(obj, dict):
        return obj
    return obj.to_dict()
