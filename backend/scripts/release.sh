#!/usr/bin/env bash

BASE_DIR="$( cd "$(dirname "$0")" ; pwd -P )/.."
python ${BASE_DIR}/manage.py migrate
python ${BASE_DIR}/manage.py collectstatic --noinput -v 0
