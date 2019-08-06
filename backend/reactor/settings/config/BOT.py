from os import getenv

TG_BOT_TOKEN = getenv('TG_BOT_TOKEN')
TG_BOT_WORKERS = int(getenv('TG_BOT_WORKERS', '4'))
WEBHOOK_URL = getenv('WEBHOOK_URL')

REDIS_URL = getenv('REDIS_URL', 'redis://localhost:6379/0')

# donation
GITHUB_URL = getenv('GITHUB_URL')
PATREON_URL = getenv('PATREON_URL')
CREDIT_CARD = getenv('CREDIT_CARD')

# misc
MESSAGE_TYPES = [
    'album',
    'text',
    'photo',
    'video',
    'animation',
    'document',
    'audio',
    'sticker',
    'voice',
    'video_note',
    'contact',
    'location',
    'venue',
    'forward',
    'link',
]
CHAT_FIELDS = {
    'buttons': "permanent predefined buttons",
    'show_credits': "show who posted message",
    'columns': "number of buttons in row",
    'add_padding': "fill blank button cells",
    'allowed_types':
        'message type to be automatically reposted by bot.\n'
        f'Available types: {" ".join(sorted(MESSAGE_TYPES))}',
    'allow_reactions': "allow to add reactions",
    'force_emojis': "allow to use only emojis as reactions",
    'repost': "if true then repost messages on bot's behalf, otherwise just reply to messages",
}
MAX_NUM_BUTTONS = 25
MAX_BUTTON_LEN = 20
MAX_USER_BUTTONS_HINTS = 3
