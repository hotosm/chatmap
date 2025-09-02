import os

# Media
MEDIA_FOLDER="media"

# Debug
DEBUG = False

# API
API_URL = os.getenv("CHATMAP_API_URL", "http://localhost:8000")
API_VERSION = os.getenv("CHATMAP_API_VERSION", "1")
# Linked devices server
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8001")


# Security
SECRET_KEY = os.getenv("CHATMAP_SECRET_KEY", "4sup3rs3cret5up3rdummykey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
CHATMAP_ENC_KEY=os.getenv("CHATMAP_ENC_KEY", "0123456789ABCDEF0123456789ABCDEF")

# Redis
STREAM_KEY = "messages"
CONSUMER_GROUP = "messages-proc"
CONSUMER_NAME = "messages-01"

# Expiring time for messages (in minutes)
EXPIRING_MIN = 120
EXPIRING_MIN_MS = EXPIRING_MIN * 60 * 1000
