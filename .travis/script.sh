#!/usr/bin/env bash

set -e
shopt -s expand_aliases
alias dkc="docker-compose -f docker-compose.travis.yml"

before() {
  dkc build app
}

run() {
  dkc run app bash -c "pytest -vv --cov=. && codecov"
}

after() {
  dkc down
}

"$@"
