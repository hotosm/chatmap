# ChatMap

## Field mapping has never been easier!

Export a chat (WhatsApp, Telegram or Signal) and upload it to visualize locations, messages and media.

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

1. Export a WhatsApp, Telegram or Signal chat with shared locations
2. Upload a .zip file to this page
3. It will extract all the locations and display them on a map, together with the paired message (text or media)
4. You can also download the locations + messages as a .zip file from there

Check docs for each instant messaging app [here](https://github.com/hotosm/chatmap/blob/master/docs/apps.md).

## Advanced mode

The advanced mode provides features for user authentication and live updates with linked devices.

### User accounts

ChatMap supports two authentication modes:

- **Standalone Mode**: Uses its own Hanko instance
- **SSO Mode**: Uses login.hotosm.org

Check [docs](https://github.com/hotosm/chatmap/blob/develop/docs/auth.md) for enabling
user authentication.

### ChatMap Live

In Live mode, people can link a device to get a live stream of data and update maps in real-time,
even with locations coming from direct messages, not only groups, and without the need of manually
exporting chats.

Check [docs](https://github.com/hotosm/chatmap/blob/develop/docs/live.md) for enabling
the Live feature.

## Roadmap

✅ Done
⚙️ In progress

<!-- prettier-ignore-start -->
| Status | Feature |
|:--:| :-- |
|✅| [Support audio](https://github.com/hotosm/chatmap/issues/5) - Thanks [Oscar](https://github.com/oxcar)!|
|✅| Link a device and get a stream of locations + content (live community reporting)|
|✅| Backend with user authentication and saved maps |
|✅| [Live Stream of Data](https://github.com/hotosm/chatmap/issues/54)
|✅| [Serve data from ChatMap](https://github.com/hotosm/chatmap/issues/29)
|⚙️| [Website re-design](https://github.com/hotosm/chatmap/issues/52)
|⚙️| [Save data directly in ChatMap](https://github.com/hotosm/chatmap/issues/64)
|⚙️| [Map options](https://github.com/hotosm/chatmap/issues/56)
|⚙️| [User profile](https://github.com/hotosm/chatmap/issues/58)
| | [Content timeline](https://github.com/hotosm/chatmap/issues/7) |
| | Form for user content licensing |
| | [Attach both image and text to a location](https://github.com/hotosm/chatmap/issues/1) |
| | ChatBot for creating automated surveys
| | [Integration for OSM editing](https://github.com/hotosm/chatmap/milestone/3)
| | [Upload content to Panoramax](https://github.com/hotosm/chatmap/issues/20) 

Contributors are welcome!

## Licensing

This is free software! you may use this project under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
