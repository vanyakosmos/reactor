from datetime import timedelta
from os import getenv

STATS_EXPIRATION_SECONDS = int(getenv('STATS_EXPIRATION_SECONDS', 5 * 60))  # default: 5 min
STATS_EXPIRATION_DELTA = timedelta(seconds=STATS_EXPIRATION_SECONDS)
STATS_MAX_RESULTS = int(getenv('STATS_MAX_RESULTS', 10))
