#!/usr/bin/env bash

set -e

apt -y update
apt -y install lsb-release
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)"-pgdg main | tee /etc/apt/sources.list.d/pgdg.list
apt -y update
apt -y install postgresql-client-11
