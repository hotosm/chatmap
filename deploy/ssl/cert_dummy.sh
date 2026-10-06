# This script generates dummy self-signed SSL certificates so Nginx can run for the first time

sudo mkdir -p "deploy/certbot/conf/live/$CHATMAP_SITE_DOMAIN"

if [ ! -f "deploy/certbot/conf/live/$CHATMAP_SITE_DOMAIN/fullchain.pem" ]; then
  echo "Certificates not found. Generating dummy certificates..."

  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "deploy/certbot/conf/live/$CHATMAP_SITE_DOMAIN/privkey.pem" \
    -out "deploy/certbot/conf/live/$CHATMAP_SITE_DOMAIN/fullchain.pem" \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=$CHATMAP_SITE_DOMAIN"
  touch deploy/certbot/conf/live/$CHATMAP_SITE_DOMAIN/dummy
  echo "Dummy certificates generated successfully."
else
  echo "File exists: deploy/certbot/conf/live/$CHATMAP_SITE_DOMAIN/fullchain.pem"
fi
