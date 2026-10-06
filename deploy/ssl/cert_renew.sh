#!/bin/bash
# Request cert renewal
docker compose run --rm chatmap-certbot certonly --webroot \
  --webroot-path=/var/www/certbot -d $CHATMAP_SITE_DOMAIN --non-interactive --agree-tos \
  -m $CHATMAP_SITE_ADMIN_EMAIL --no-eff-email --force-renewal
# Reload Nginx
docker compose exec chatmap-nginx nginx -s reload
