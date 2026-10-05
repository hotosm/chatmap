# This script generates dummy self-signed SSL certificates so Nginx can run for the first time

mkdir -p "deploy/certbot/conf/archive/$CHATMAP_SITE_DOMAIN"
mkdir -p "deploy/certbot/conf/live/$CHATMAP_SITE_DOMAIN"

if [ ! -f "deploy/certbot/conf/live/$CHATMAP_SITE_DOMAIN/fullchain.pem" ]; then
  echo "Certificates not found. Generating dummy certificates..."

  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "deploy/certbot/conf/archive/$CHATMAP_SITE_DOMAIN/privkey.pem" \
    -out "deploy/certbot/conf/archive/$CHATMAP_SITE_DOMAIN/fullchain.pem" \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=$CHATMAP_SITE_DOMAIN"

  ln -sf "deploy/certbot/conf/archive/$CHATMAP_SITE_DOMAIN/privkey.pem" "deploy/certbot/conf/live/$CHATMAP_SITE_DOMAIN/privkey.pem"
  ln -sf "deploy/certbot/conf/archive/$CHATMAP_SITE_DOMAIN/fullchain.pem" "deploy/certbot/conf/live/$CHATMAP_SITE_DOMAIN/fullchain.pem"
  
  echo "Dummy certificates generated successfully."
else
  echo ""
fi
