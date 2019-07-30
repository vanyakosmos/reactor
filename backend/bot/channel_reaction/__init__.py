"""
# REACTION TO POSTS FROM CHANNEL

```
user: click "add reaction"
tg: redirect to the chat with bot with '/start <message_id>'
user: click "start"
> trigger /start command: save message_id, change dialog state

user: send emoji
> trigger message handler: validate message,
    update markup of message fetched using preserved message_id,
    keep the same dialog state
```
"""

from .commands import command_start
from .message_handlers import handle_reaction_response
