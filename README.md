# ChatMap

Export a chat (WhatsApp, Telegram or Signal) and upload it to visualize locations, messages and media.

It was developed to help emergency services and humanitarian organizations to get
locations from people in the field during disasters and emergencies, but it can
be used for anything else.

### Try it here! [chatmap.hotosm.org](https://chatmap.hotosm.org)

---

<img width="957" alt="Screenshot 2025-01-12 at 5 46 39 PM" src="https://github.com/user-attachments/assets/27356785-b5ed-424d-b45e-63af4fc87673" />

## Install and run

```bash
yarn install
yarn start
```

Test with `yarn test`.

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
|⚙️| Add a new feature to tag content |
|⚙️| Attach both image and text to a location |
|⚙️| Support audio |

## Licensing

Copyright 2024 Emilio Mariscal

This is free software! you may use this project under the terms of the GNU General Public License (GPL) Version 3.
