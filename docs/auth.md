# ChatMap with user accounts

ChatMap supports two authentication modes:

- **SSO Mode**: Uses login.hotosm.org (production)
- **Standalone Mode**: Local Hanko instance (development)

### Dev Mode (hot reload)

Full development environment with hot reload for frontend and backend:

```bash
# Start all services
docker compose -f compose.dev.yml up
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8001 |
| Hanko | http://localhost:8002 |
| MailHog | http://localhost:8025 |

### SSO Mode (production)

Uses login.hotosm.org for authentication:

```bash
# Default config already points to SSO
docker compose up
```

