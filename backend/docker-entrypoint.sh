#!/bin/sh
set -e
# Her açılışta şemayı güncel tut
alembic upgrade head
exec "$@"
