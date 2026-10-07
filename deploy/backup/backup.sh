#!/bin/bash
echo "Exporting database backup ..."
docker exec -ti chatmap-chatmap-db-1 pg_dump -U admin chatmap | gzip > backup.sql.gz
echo "Creating media files backup ..."
find $HOME/chatmap/media -type f -mmin -1500 -print0 | xargs -r -0 tar -cvzf media.tgz
python3 $HOME/backup.py
