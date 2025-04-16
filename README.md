# ChatMap

Export a chat (WhatsApp, Telegram or Signal) and upload it to visualize locations, messages and media.

It was developed to help emergency services and humanitarian organizations to get
locations from people in the field during disasters and emergencies, but it can
be used for anything else.

### Try it here! [chatmap.hotosm.org](https://chatmap.hotosm.org)

Check this quick [video-tutorial](https://www.youtube.com/watch?v=ScHgVhyj1aw) (2:47) for more info about how to use it.

---

<img width="959" alt="Screenshot 2025-04-11 at 12 10 04 PM" src="https://github.com/user-attachments/assets/1f045037-02d9-458f-ba65-8d1bad5eb983" />

## Install and run

```bash
yarn install
yarn start
```

Test with `yarn test`.

Check the [dev](https://github.com/hotosm/chatmap/tree/dev) branch for latest development version.

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
|✅| Support multiple instant messaging apps (WhatsApp, Telegram, Signal) |
|✅| Support video |
|✅| Download a .zip file with GeoJSON and images to save the map in umap.hotosm.org |
|✅| Add tests |
|✅| Include videos in .zip download |
|✅| [Add a new feature to tag content](https://github.com/hotosm/chatmap/issues/6) |
|⚙️| [Attach both image and text to a location](https://github.com/hotosm/chatmap/issues/1) |
|⚙️| [Support audio](https://github.com/hotosm/chatmap/issues/5) |

## Licensing

Copyright 2024 Emilio Mariscal

This is free software! you may use this project under the terms of the GNU General Public License (GPL) Version 3.
