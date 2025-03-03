## WhatsApp

Check this [video-tutorial](https://www.youtube.com/watch?v=ScHgVhyj1aw) (2:47 min).

Go to the group you want to export and select:

> Export chat

Select "Attach media" if you want to include media.

Import the .zip file. If you don't need media, you can import the .txt file only.

## Telegram

You'll need [Telegram Desktop](https://desktop.telegram.org).

Go to the group you want to export and from the top-right menu select:

> Export chat history

Check "Photos" if you want to include media, select "JSON" for the Format,
and click "Export"

A folder will be created. If you want to include media you should compress
the whole folder into a .zip file and import it into ChatMap.

If you don't need media, you can import the .json file only.

## Signal

You'll need [Signal Desktop](https://signal.org/download/). Only the messages created after installing
it will be available.

Install [Sigtop](https://github.com/tbvdm/sigtop) to export the chat.

Then, from the command line, run this to export messages:

`sigtop msg -c <name the group>`

And if you want to include media:

`sigtop att -c <name the group>`

A .txt file and a folder for media will be created.

Compress everything into a .zip file and import it into ChatMap.

If you don't need media, you can import the .txt file only.

