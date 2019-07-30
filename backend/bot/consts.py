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
    'force_emojis': "allow to use only emojis as reaction",
    'repost': "if true then repost messages on bot's behalf, otherwise just reply to messages",
}
MAX_NUM_BUTTONS = 25
