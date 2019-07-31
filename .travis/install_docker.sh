#!/usr/bin/env bash

set -o errexit

install_engine() {
  echo "update docker engine"
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
  sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
  sudo apt-get update
  sudo apt-get -y -o Dpkg::Options::="--force-confnew" install docker-ce
  docker --version
}

install_compose() {
  echo "update docker-compose"
  DOCKER_COMPOSE_VERSION=1.23.2
  sudo rm /usr/local/bin/docker-compose
  curl -L https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-`uname -s`-`uname -m` > docker-compose
  chmod +x docker-compose
  sudo mv docker-compose /usr/local/bin
  docker-compose --version
}

main() {
  install_engine
  install_compose

  docker info
}


main
