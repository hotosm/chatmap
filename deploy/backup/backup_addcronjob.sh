(crontab -l ; echo "0 0 * * * $HOME/chatmap/deploy/backup/backup.sh") | crontab -
