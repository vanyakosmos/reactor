MESSAGE_TYPES = {'photo', 'video', 'animation', 'text', 'link', 'forward', 'album'}
CHAT_FIELDS = {
    'buttons': 'permanent predefined buttons',
    'show_credits': 'show who posted message',
    'columns': 'number of buttons in row',
    'add_padding': 'fill blank button cells',
    'allowed_types':
        'message type to be automatically reposted by bot. '
        f'Available types: {"".join(sorted(MESSAGE_TYPES))}',
    'allow_reactions': 'allow to add reactions',
    'force_emojis': 'allow to use only emojis as reaction',
}
