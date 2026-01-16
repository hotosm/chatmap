import os

# Media
MEDIA_FOLDER="media"

# Debug
DEBUG = (os.getenv('CHATMAP_API_DEBUG', 'false').lower() == 'true')

# API
API_URL = os.getenv("CHATMAP_API_URL", "http://localhost:8000")
API_VERSION = os.getenv("CHATMAP_API_VERSION", "1")

# Linked devices server
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8001")

# Security
SECRET_KEY = os.getenv("CHATMAP_SECRET_KEY", "4sup3rs3cret5up3rdummykey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("CHATMAP_ACCESS_TOKEN_EXPIRE_MINUTES", 120))
CHATMAP_ENC_KEY = os.getenv("CHATMAP_ENC_KEY", "0123456789ABCDEF0123456789ABCDEF")

# Redis
STREAM_KEY = "messages"
CONSUMER_GROUP = "messages-proc"
CONSUMER_NAME = "messages-01"

# Expiring time for messages (in minutes)
EXPIRING_MIN = int(os.getenv("CHATMAP_EXPIRING_MIN", 30))
EXPIRING_MIN_MS = EXPIRING_MIN * 60 * 1000

# Database
CHATMAP_DB = os.getenv("CHATMAP_DB", "chatmap")
CHATMAP_DB_USER = os.getenv("CHATMAP_DB_USER", "admin")
CHATMAP_DB_PASSWORD = os.getenv("CHATMAP_DB_PASSWORD", "0123456789ABCDEF0123456789ABCDEF")
CHATMAP_DB_PORT = os.getenv("CHATMAP_DB_PORT", 5432)
CHATMAP_DB_HOST = os.getenv("CHATMAP_DB_HOST", "localhost")

# Stream listener time
STREAM_LISTENER_TIME = int(os.getenv("CHATMAP_STREAM_LISTENER_TIME", 10))
DISABLE_STREAM_CLEANUP = (os.getenv('CHATMAP_DISABLE_STREAM_CLEANUP', 'false').lower() == 'true')

# CORS setup
CORS_ORIGINS = os.getenv("CHATMAP_CORS_ORIGINS", "localhost,127.0.0.1").split(",")
