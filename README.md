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

* [Live Stream of Data](https://github.com/hotosm/chatmap/milestone/1)
* [Save and serve data directly in ChatMap](https://github.com/hotosm/chatmap/milestone/2)
* [Integration for OSM editing](https://github.com/hotosm/chatmap/milestone/3)

See also the [roadmap board](https://github.com/orgs/hotosm/projects/46).

Contributors are welcome!

## Licensing

Copyright 2024 Emilio Mariscal

This is free software! you may use this project under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
