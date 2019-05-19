#!/usr/bin/env bash

set -e

if [[ ${1:-prod} == 'dev' ]]; then
    echo "running DEV server..."
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "running PROD server..."
    python manage.py migrate
    python manage.py collectstatic --noinput
    # todo
    # exec gunicorn fba.wsgi --workers 4 --bind 0.0.0.0:8000
    exec python manage.py runserver 0.0.0.0:8000
fi
