# ChatMap

[![Deploy master to chatmap.hotosm.org](https://github.com/hotosm/chatmap/actions/workflows/build_deploy_master.yml/badge.svg)](https://github.com/hotosm/chatmap/actions/workflows/build_deploy_master.yml)

## Field mapping has never been easier!

Export a chat (WhatsApp, Telegram or Signal) and open it to visualize locations, messages and media.

### Try it here! [chatmap.hotosm.org](https://chatmap.hotosm.org)

Check this quick [video-tutorial](https://www.youtube.com/watch?v=ScHgVhyj1aw) (2:47) for more info about how to use it.

<img width="1512" height="853" alt="Screenshot 2026-01-21 at 9 27 42 AM" src="https://github.com/user-attachments/assets/f14412a4-7241-4840-8e33-937fdedaa37b" />

---

## Install and run

```bash
cd chatmap-ui
yarn install
yarn start
```

Test with `yarn test`.

### How to use it?

Create a group and ask people to post locations and messages. Each location will be paired 
with the closest message from the same user.

1. Export a WhatsApp, Telegram or Signal chat with shared locations, to a zip file
2. Open the .zip file with ChatMap
3. It will extract all the locations and display them on a map, together with the paired message (text or media)
4. You can also download the locations + messages as a .zip file from there, and open it again if needed!

Check docs for each instant messaging app [here](https://github.com/hotosm/chatmap/blob/master/docs/apps.md).

## Advanced mode

The advanced mode provides features for user authentication, saving and publishing maps, and live updates with linked devices.

```bash
docker compose -f compose.dev.yml up
```

Then open http://localhost:5173 and create an account using any e-mail.

Check [authentication docs](https://github.com/hotosm/chatmap/blob/develop/docs/auth.md) and [Live feature docs](https://github.com/hotosm/chatmap/blob/develop/docs/live.md).

## Roadmap 2026

✅ Done
⚙️ In progress

<!-- prettier-ignore-start -->
| Status | Feature |
|:--:| :-- |
|✅| [Serve data from ChatMap](https://github.com/hotosm/chatmap/issues/29)
|✅| [Website re-design](https://github.com/hotosm/chatmap/issues/52)
|✅| [Map options](https://github.com/hotosm/chatmap/issues/56)
|✅| [User profile](https://github.com/hotosm/chatmap/issues/58)
|✅| [Save data directly in ChatMap](https://github.com/hotosm/chatmap/issues/64) - Thanks [Abraham](https://github.com/categulario)!
|✅| [Update a saved map with new data](https://github.com/hotosm/chatmap/issues/60) - Thanks [Abraham](https://github.com/categulario)!
|✅| [Attach both image and text to a location](https://github.com/hotosm/chatmap/issues/1)
|⚙️| [ChatBot for creating automated surveys](https://github.com/hotosm/chatmap/issues/186)
|⚙️| [Upload content to Panoramax](https://github.com/hotosm/chatmap/issues/20) 
|⚙️| User content licensing options |
| | [Content timeline](https://github.com/hotosm/chatmap/issues/7)
| | Content filtering options |
| | Tagger view |

## Licensing

This is free software! you may use this project under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
