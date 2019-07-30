"""
React to posts with replies.

- `+EMOJI` - add new button.
- `.~` - change post's structure (eg: make it anonymous, remove buttons),
    only allowed for post's owner.
"""

from .replies_handlers import handle_reaction_reply, handle_magic_reply
