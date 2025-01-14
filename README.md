# ChatMap

Export a chat from the app (WhatsApp, Telegram or Signal) and visualize the locations shared in the conversation.

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

## How to use it?

Create a group and ask people to post a locations and messages. Each location will be paired 
with the closest message from the same user.

1. Export a WhatsApp, Telegram or Signal chat with shared locations
2. Upload a .zip file to this page
3. It will extract all the locations and display them on a map, together with the paired message (text or media)
4. You can also download the locations + messages as a GeoJSON file from there

## WhatsApp

Check this [video-tutorial](https://www.youtube.com/watch?v=ScHgVhyj1aw) (2:47 min).

Go to the group you want to export and select:

> Export chat

Select "Attach media" if you want to include media.

Import the .zip file. If you don't need media, you can import the .txt file only.

## Telegram

Download the Telegram Desktop app from the website:

https://desktop.telegram.org

Go to the group you want to export and from the top-right menu select:

> Export chat history

Check "Photos" if you want to include media, select "JSON" for the Format,
and click "Export"

A folder will be created. If you want to include media you should compress
the whole folder into a .zip file and import it into ChatMap.

If you don't need media, you can import the .json file only.

## Signal

You'll need Signal Desktop. Only the messages created after installing
Signal Desktop will be available.

Install Sigtop to export the chat:

https://github.com/tbvdm/sigtop

Then, from the command line, run this to export messages:

`sigtop msg -c <name the group>`

And if you want to include media:

`sigtop att -c <name the group>`

A .txt file and a folder for media will be created.

Compress everything into a .zip file and import it into ChatMap.

If you don't need media, you can import the .txt file only.

## Licensing

Copyright 2024 Emilio Mariscal

This is free software! you may use this project under the terms of the GNU General Public License (GPL) Version 3.
