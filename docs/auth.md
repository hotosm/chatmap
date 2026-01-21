# ChatMap with user accounts

# [ THIS DOCUMENT HAS TO BE UPDATED ]

ChatMap supports two authentication modes:

- **SSO Mode**: Uses login.hotosm.org (production)
- **Standalone Mode**: Local Hanko instance (development)

### Dev Mode (hot reload)

Full development environment with hot reload for frontend and backend:

```bash
# Copy config for local Hanko
cp chatmap-ui/public/config.dev.json chatmap-ui/public/config.json

# Start all services
docker compose -f compose.dev.yml up
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8001 |
| Hanko | http://localhost:8002 |
| MailHog | http://localhost:8025 |

### Standalone Mode (production images + local Hanko)

Uses production Docker images but with local Hanko for auth:

```bash
# Copy config for standalone
cp config/config.standalone.json deploy/frontend/config.json

# Start with standalone profile
docker compose --profile standalone up
```

### SSO Mode (production)

Uses login.hotosm.org for authentication:

```bash
# Default config already points to SSO
docker compose up
```

### Google OAuth (optional)

Enable Google Sign-In for standalone/dev mode:

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create OAuth 2.0 Client ID (Web application)
3. Add authorized redirect URI: `http://localhost:8002/thirdparty/callback`
4. Copy credentials to `.env`:

```bash
cp .env.example .env
# Edit .env:
GOOGLE_ENABLED=true
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

5. Restart services to apply changes

### Deploy Configuration

For CI/CD deployment, configure these GitHub variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `HANKO_API_URL` | Hanko auth endpoint | `https://dev.login.hotosm.org` |
| `CHATMAP_API_URL` | API base URL | `https://chatmap-dev.hotosm.org` |
| `CHATMAP_ENABLE_LIVE` | Enable live mode | `true` / `false` |

For standalone deployment, also configure SMTP and optionally Google OAuth secrets.