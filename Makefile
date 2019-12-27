start:
	docker-compose up bot db

restart_bot:
	docker-compose restart -t 0 bot
