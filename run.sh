#! /usr/bin/env bash

docker rm crypto_parser -f
docker run --name crypto_parser -v "${PWD}:/code" -d crypto_parser
