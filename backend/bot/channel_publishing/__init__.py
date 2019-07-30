"""
# PUBLISHING IN CHANNEL

## in user-bot chat:
```
user: /create
> trigger "create" command handler: change dialog state

bot: now send message to publish
user: <message>
> trigger message handler: save content of message

bot: now pick buttons
user: <pick buttons, eg "👍　👎">
> trigger message handler: retrieve message to publish, save chosen buttons

bot: <publishable post>
user: click "publish"
tg: prompts to select chat

user: pick chat
tg: inserts inline query with message-to-publish ID
> trigger inline inline publishing options (essentially just 1 result for specified ID)

user: select post from inline query results
tg: creates message based on selected option
> trigger inline query respond: add message to DB, append markup to the created message
```
"""

from .commands import command_create
from .inline_handlers import handle_publishing, handle_publishing_options
from .message_handlers import handle_create_buttons, handle_create_start
