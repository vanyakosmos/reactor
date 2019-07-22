#!/usr/bin/env bash

SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"
python ${SCRIPTPATH}/../manage.py migrate
python ${SCRIPTPATH}/../manage.py collectstatic --noinput -v 0
