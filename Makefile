schema:
	./manage.py graph_models core -o schema.png

test:
	cd backend && pytest -vv

hardmig:
	./backend/manage.py makemigrations
	./backend/manage.py migrate

rbot:
	docker-compose restart bot
