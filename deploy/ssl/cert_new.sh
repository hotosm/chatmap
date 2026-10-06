#!/bin/bash
# Remove dummy cert
if [ -f "deploy/certbot/conf/live/$CHATMAP_SITE_DOMAIN/dummy" ]; then
  echo "Removing existing certificates"
  rm -rf /etc/letsencrypt/live/*
  rm -rf /etc/letsencrypt/archive/*
  rm -rf /etc/letsencrypt/renewal/*
  # Request cert for first time
  docker compose run --rm certbot certonly --webroot \
    --webroot-path=/var/www/certbot -d $CHATMAP_SITE_DOMAIN --non-interactive --agree-tos \
    -m $CHATMAP_SITE_ADMIN_EMAIL --no-eff-email --force-renewal
  docker exec chatmap-chatmap-nginx-1 nginx -s reload
else
  echo "No dummy cert found."
fi
