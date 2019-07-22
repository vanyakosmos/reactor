#!/usr/bin/env bash

set -e

port=${PORT:-8000}

if [[ ${1:-prod} == 'dev' ]]; then
    echo "running DEV server..."
    exec python manage.py runserver 0.0.0.0:${port}
else
    echo "running PROD server..."
    exec gunicorn reactor.wsgi --bind 0.0.0.0:${port}
fi
