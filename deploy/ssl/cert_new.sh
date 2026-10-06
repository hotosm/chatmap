#!/bin/bash
# Remove dummy cert
if [ -f "deploy/certbot/conf/live/$CHATMAP_SITE_DOMAIN/dummy" ]; then
  echo "Removing existing certificates"
  sudo rm -rf deploy/certbot/conf/live/*
  sudo rm -rf deploy/certbot/conf/archive/*
  sudo rm -rf deploy/certbot/conf/renewal/*
  # Request cert for first time
  docker compose run --rm chatmap-certbot certonly --webroot \
    --webroot-path=/var/www/certbot -d $CHATMAP_SITE_DOMAIN --non-interactive --agree-tos \
    -m $CHATMAP_SITE_ADMIN_EMAIL --no-eff-email --force-renewal
  docker compose -f compose.yml up -d chatmap-nginx --force-recreate
  # Add renew cronjob
  (crontab -l ; echo "0 0 * * * CHATMAP_SITE_DOMAIN=$CHATMAP_SITE_DOMAIN CHATMAP_SITE_ADMIN_EMAIL=$CHATMAP_SITE_ADMIN_EMAIL $PWD/deploy/ssl/cert_renew.sh") | crontab -
else
  echo "No dummy cert found."
fi
