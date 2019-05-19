import redis
from django.conf import settings

redis_client = redis.Redis.from_url(settings.REDIS_URL)


def save_media_group(media_group, expire=60):
    """Save media_group to redis storage and return True if it didn't exist yet."""
    key = f'media_group:{media_group}'
    if redis_client.exists(key):
        return False
    redis_client.set(key, 1, ex=expire)
    return True
