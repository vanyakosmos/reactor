schema:
	./manage.py graph_models core -o schema.png

test:
	pytest -vv

hardmig:
	./manage.py makemigrations
	./manage.py migrate
