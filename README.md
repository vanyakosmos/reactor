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
- [ ] allow to change group chat settings from private chat
- [ ] reactions for channels with posting from private chat
- [ ] add web UI for chat administration and statistics

#### misc:

- [ ] restructure django settings
- [ ] add automatic backups
- [ ] reactions/db caching and/or remake bot (while keeping django admin/api) using faster lang (eg golang)
- [ ] add some tests
- [ ] add CI
