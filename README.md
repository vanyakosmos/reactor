# reactor

Telegram bot that automatically add reaction buttons to messages (similar to slack/discord).


## TODOs

#### features:

- [x] add basic bot functionality: messages reposting, reply reactions, chat default buttons
- [x] add reactions to albums without reposting each photo (simple reply with buttons)
- [x] show credits of original message: who posted, from whom forwarded
- [x] allow to change bot settings only to chat's admins
- [ ] add more settings: 
  - [x] number of buttons in row
  - [x] types of messages to be reposted
  - [x] buttons padding
  - [x] hide/show credits
  - [ ] reply the original message instead of reposting it
  - [ ] allow to disable custom reactions
  - [ ] regulate button size (max string length)
  - [ ] add emoji enforcing
- [x] add forced processing/ignoring of message (using message prefix)
- [x] reactions for channels via inline interface
- [ ] add setting for inline posting
- [ ] add web UI for chat administration and statistics

#### misc:

- [ ] restructure django settings
- [ ] add automatic backups
- [ ] reactions/db caching and/or remake bot (while keeping django admin/api) using faster lang (eg golang)
- [ ] add some tests
- [ ] add CI
