#!/bin/sh
# Kullanım: ./deploy/restore.sh backups/marketkiyas-YYYYMMDD-HHMMSS.dump
# Dikkat: mevcut veritabanının üzerine yazar.
set -eu
f="${1:?yedek dosyasi gerekli}"
C="docker compose -f docker-compose.prod.yml"
$C stop api worker aktuel weekly-menus purge-guests
$C exec -T db pg_restore -U marketkiyas -d marketkiyas --clean --if-exists --no-owner < "$f"
$C up -d
