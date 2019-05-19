# reactor

Telegram bot that automatically add reaction buttons to messages (similar to slack/discord).

## TODO

- [x] add basic bot functionality: messages reposting, reply reactions, chat default buttons
- [ ] add reactions to albums without reposting each photo
- [x] show credits of original message: who posted, from whom forwarded
- [ ] allow to change bot settings only to chat admins
- [ ] add more settings: 
  - [x] number of buttons in row
  - [x] types of messages to be reposted
  - [x] buttons padding
  - [x] hide/show credits
  - [ ] reply the original message instead of reposting
- [ ] web UI for chat administration and statistics
- [ ] reactions for channels
- [ ] reactions/db caching and/or remake bot (while keeping django admin/api) using faster lang (eg golang)
