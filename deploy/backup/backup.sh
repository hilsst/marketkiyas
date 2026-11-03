#!/bin/sh
# Günde bir pg_dump alır, KEEP_DAYS günden eskileri siler.
set -eu
mkdir -p /backups
while true; do
  f="/backups/marketkiyas-$(date +%Y%m%d-%H%M%S).dump"
  if pg_dump -Fc -f "$f.tmp"; then
    mv "$f.tmp" "$f"
    echo "yedek alindi: $f"
  else
    rm -f "$f.tmp"; echo "YEDEK BASARISIZ" >&2
  fi
  find /backups -name 'marketkiyas-*.dump' -mtime +"${KEEP_DAYS:-14}" -delete
  sleep 86400
done
