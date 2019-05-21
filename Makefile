schema:
	./backend/manage.py graph_models core -o schema.png

test:
	cd backend && pytest -vv

hardmig:
	./backend/manage.py makemigrations
	./backend/manage.py migrate

start:
	docker-compose up bot db

restart_bot:
	docker-compose restart -t 0 bot
