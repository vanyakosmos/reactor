# reactor

Telegram bot that automatically add reaction buttons to messages (similar to slack/discord).


## Usage in group

- add bot to the group
- give him admin rights (so it could delete messages)
- send message with media content -> bot will repost it with buttons
- reply to that message with "+button" to add new reaction
- use /help /settings /edit to monitor and control bot's behaviour


## Usage in channel

- go to private chat with bot
- /create
- send message that you would like to "reactify"
- go to the channel and publish that message via inline interface (`@botname uuid` -> pick message)
- press "vote" to add new reaction -> will be redirected to the private chat with bot -> send emoji/sticker


## Magic Marks

(groups only)

Apply special action by adding prefix to message's text/caption.

```
# force bot to ignore message
.-text

# force bot to repost message
.+text

# force bot to repost message on his behalf
.++text
 
# hide credits
.~text

# show "a, b" buttons instead of default ones in that chat
.``text
.`👍 👎`text

# combine marks
.+~`👍 👎`text
```

Some magic marks also work with replies (if you are the original poster of that message)
```
# toggle credits
.~

# change buttons
.``
.`👍 👎`
```


## TODOs

#### features:

- [x] add basic bot functionality: messages reposting, reply reactions, chat default buttons
- [x] add reactions to albums without reposting each photo (simple reply with buttons)
- [x] show credits of original message: who posted, from whom forwarded
- [x] allow to change bot settings only to chat's admins
- [x] add more chat settings: 
  - [x] number of buttons in row
  - [x] types of messages to be reposted
  - [x] buttons padding
  - [x] hide/show credits
  - [x] reply to the original message instead of reposting it
  - [x] allow to disable reactions
  - [x] add emoji enforcing
- [x] add forced processing/anonymity/ignore/custom buttons via magic marks (text/caption prefixes)
- [x] reactions for channels via inline interface
- [x] add setting for inline posting
- [ ] gather and store chat statistics
- [ ] add web UI for chat administration and statistics

#### misc:

- restructure django settings
- refactor this mess
- add clean up cronjob (remove old messages>buttons>reactions)
- add automatic backups
- add some tests
- add CI
- apply reactions in bulk on high load
