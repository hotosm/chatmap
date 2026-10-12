#!/bin/bash
echo "Exporting database backup ..."
docker compose -f $HOME/chatmap/compose.yml -ti chatmap-db pg_dump -U admin chatmap | gzip > backup.sql.gz
echo "Creating media files backup ..."
find $HOME/chatmap/media -type f -mmin -1500 -print0 | xargs -r -0 tar -cvzf media.tgz
python3 $HOME/chatmap/deploy/backup/backup.py
