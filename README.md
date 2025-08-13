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

## ChatMap Live + linked devices

In Live mode, people can link a device to get a live stream of data and update maps in real-time,
even with locations coming from direct messages, not only groups, and without the need of manually
exporting chats.

Check [docs](https://github.com/hotosm/chatmap/blob/feature/live/docs/live.md) for enabling
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

## Product roadmap

✅ Done
⚙️ In progress

<!-- prettier-ignore-start -->
| Status | Feature |
|:--:| :-- |
|✅| [Support audio](https://github.com/hotosm/chatmap/issues/5) - Thanks [Oscar](https://github.com/oxcar)!|
|✅| Link a device and get a stream of locations + content (live community reporting)|
|✅| Backend with user authentication and saved maps |
|⚙️| Map settings
|⚙️| User profile
| | [Attach both image and text to a location](https://github.com/hotosm/chatmap/issues/1) |
| | [Content timeline](https://github.com/hotosm/chatmap/issues/7) |

## Licensing

Copyright 2024 Emilio Mariscal

This is free software! you may use this project under the terms of the GNU General Public License (GPL) Version 3.
