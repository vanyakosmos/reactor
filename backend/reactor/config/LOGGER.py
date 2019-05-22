import logging


def add_color(string: str, color, just=0):
    string = string.rjust(just)
    return f'\033[{color}m{string}\033[0m'


# setup logging level display
levels = [
    (logging.DEBUG, add_color('DEBUG', '36', 5)),
    (logging.INFO, add_color('INFO', '32', 5)),
    (logging.WARNING, add_color('WARN', '33', 5)),
    (logging.ERROR, add_color('ERROR', '31', 5)),
    (logging.CRITICAL, add_color('CRIT', '7;31;31', 5)),
]
for level, name in levels:
    logging.addLevelName(level, name)

m = add_color(">", '36')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': f'[%(asctime)s] %(levelname)s %(name)27s:%(lineno)-3d {m} %(message)s',
            'datefmt': "%Y/%m/%d %H:%M:%S"
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'core': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'bot': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}
