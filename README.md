# ChatMap

## Field mapping has never been easier!

Export a chat (WhatsApp, Telegram or Signal) and upload it to visualize locations, messages and media.

### Try it here! [chatmap.hotosm.org](https://chatmap.hotosm.org)

Check this quick [video-tutorial](https://www.youtube.com/watch?v=ScHgVhyj1aw) (2:47) for more info about how to use it.

<img width="1001" alt="Screenshot 2025-05-08 at 5 38 46 PM" src="https://github.com/user-attachments/assets/9a9e50e0-f154-4fc3-b574-09bf54b23c67" />

---

## Install and run

```bash
cd chatmap-ui
yarn install
yarn start
```

Test with `yarn test`.

## Development

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

## ChatMap Live + linked devices

In Live mode, people can link a device to get a live stream of data and update maps in real-time,
even with locations coming from direct messages, not only groups, and without the need of manually
exporting chats.

Check [docs](https://github.com/hotosm/chatmap/blob/develop/docs/live.md) for enabling
the Live version of ChatMap with linked devices.

## How to use it?

Create a group and ask people to post locations and messages. Each location will be paired 
with the closest message from the same user.

1. Export a WhatsApp, Telegram or Signal chat with shared locations
2. Upload a .zip file to this page
3. It will extract all the locations and display them on a map, together with the paired message (text or media)
4. You can also download the locations + messages as a .zip file from there

Check docs for each instant messaging app [here](https://github.com/hotosm/chatmap/blob/master/docs/apps.md).

## How to save the map

Login into umap.hotosm.org, click "Upload" and upload the .zip !

## Roadmap

✅ Done
⚙️ In progress

<!-- prettier-ignore-start -->
| Status | Feature |
|:--:| :-- |
|✅| [Support audio](https://github.com/hotosm/chatmap/issues/5) - Thanks [Oscar](https://github.com/oxcar)!|
|✅| Link a device and get a stream of locations + content (live community reporting)|
|✅| Backend with user authentication and saved maps |
|⚙️| [Map settings](https://github.com/hotosm/chatmap/issues/37)
|⚙️| [User profile](https://github.com/hotosm/chatmap/issues/36)
| | Form for user content licensing |
| | [Attach both image and text to a location](https://github.com/hotosm/chatmap/issues/1) |
| | [Content timeline](https://github.com/hotosm/chatmap/issues/7) |
| | [Upload content to Panoramax](https://github.com/hotosm/chatmap/issues/20) 

Check the [development](https://github.com/hotosm/chatmap/blob/develop/) branch for upcoming features.

Contributors are welcome!

## Licensing

This is free software! you may use this project under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
