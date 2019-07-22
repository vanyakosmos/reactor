#!/usr/bin/env bash

set -e

PORT=${PORT:-8000}
BASE_DIR="$( cd "$(dirname "$0")" ; pwd -P )/.."

if [[ ${1:-prod} == 'dev' ]]; then
    echo "running DEV server..."
    exec python ${BASE_DIR}/manage.py runserver 0.0.0.0:${PORT}
else
    echo "running PROD server..."
    exec gunicorn reactor.wsgi --bind 0.0.0.0:${PORT} --chdir ${BASE_DIR}
fi
