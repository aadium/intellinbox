#!/bin/bash
# backup.sh
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker exec -t intellinbox_db pg_dump -U myuser -d medsynth > ./backups/$TIMESTAMP.sql
echo "Backup saved to ./backups/$TIMESTAMP.sql"