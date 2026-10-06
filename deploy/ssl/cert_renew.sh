#!/bin/bash
# Run certbot renewal
docker run -it --rm --name certbot \
  -v $(pwd)/certbot/conf:/etc/letsencrypt \
  -v $(pwd)/certbot/www:/var/www/certbot \
  -e CR_EMAIL="$CHATMAP_SITE_ADMIN_EMAIL" \
  certbot/certbot renew --webroot -w /var/www/certbot

# Reload Nginx to pick up the new certificates
docker exec chatmap-chatmap-nginx-1 nginx -s reload
