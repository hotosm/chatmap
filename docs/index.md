# ChatMap Documentation and FAQs

https://chatmap.hotosm.org/

## What is ChatMap?

ChatMap is a simple browser-based tool which parses WhatsApp, Telegram and Signal group conversations to visualize the locations shared in the chat. It automatically attaches any text, images or video to the most recently shared location by the same user. 

The results are downloadable in a spatial format. 

In the classic mode, ChatMap does not retrieve information from a group chat in real time, instead a group member must export the group chat and upload it into ChatMap to create ‘one-off’ maps. In the advanced Live mode, content is available in real time,
without the need to export the chat.

### How to get started

Create a WhatsApp, Telegram or Signal group and give it a relevant name, e.g. ‘School location sharing Ecuador’. 

## Frequently Asked Questions (FAQ)

### How to share an image /video/audio

In the group, share your location by selecting the paperclip icon (Android), selecting ‘Location’ and ‘Send your current location’. Wait a few seconds before sending your location and you may notice the location accuracy improving (reducing to only a few meters). 

If you’re using WhatsApp on an iPhone select the + icon to the left of the text field and select ‘Location’ and ‘Send your current location’. Waiting a few seconds before pressing share location will improve the accuracy. 

After sharing your location, take a photo, video or audio in WhatsApp ensuring it is shared to the group. 

### How to share some text

Share your location by following the same steps as above, but this time after sharing your location, write a text message in the group chat. 

If you are the person leading this collection effort, consider laying out specific guidelines for sharing text (e.g. please keep to a maximum of five words). 

### What can be shared with the location?

One image, video, audio or one piece of text. If more information is needed for the same location (e.g. image with associated text or several images) the location has to be re-shared for each additional image or piece of text. 

Note that this does not merge this information on the final map, it just creates two separate points which are very close together, each with unique information. 

### Can I share the text or image first and then share location? 

Yes, the mapping tool looks for the location and then the most recently shared media associated with that location and the same contact. So if the media is shared before or after the location it does not make a difference. 

### How do I know who shared the information?

The final map will have the names of the people who shared the image/text and this is pulled from group chat based on the names as saved in the contacts list of the person that exports the chat.  

### Will an image with attached text add both the text and image? 

No, it will only add the image, the text will not be added to the map. 

### How to generate a map

In your WhatsApp group select the three dots symbol in the top right corner of WhatsApp and select ‘More’ > ‘Export chat’ > Include media. Save this zipped folder somewhere you can access from a computer or mobile (e.g. a Google Drive). Then, go to:

https://chatmap.hotosm.org/

Select upload and choose the zipped folder and it will generate a map. You will need an internet connection for this last step.

### Who can generate the map? 

Any group member can export the messages to create a map and anyone can access ChatMap (no login required). 

### Who can see the map? 

Only the map creators can directly see the map results in ChatMap (it does not generate a unique link for viewing the results). 

If you want to share the results more widely this can be done by downloading the results from ChatMap as a GeoJSON (selecting the ‘Download’ button does this) and uploading to a sharable custom web map such as uMap.

If the advanced live mode with authentication is enabled, you can share your map as a public link.

### How do I update the map?

Re-export the chat and re-upload it to ChatMap. 

If auth + live mode is enabled, the map will be updated automatically.

### Can group members delete information that they have shared?

Yes, within 60 hours of posting, the author of any image or text can long press the image or text in WhatsApp > Select the bin icon along the top and select ‘Delete  for everyone’. This will then be reflected in ChatMap as long as the chat is exported after the deletions have been made. In the final map this will show as a location but with a `<You deleted this message>` entry for both images as text. 

WhatsApp group admins can delete image or text posts from anyone in the group within 60 hours of posting and this will also be reflected in ChatMap. 

In WhatsApp the group creator (automatically an admin) can add other admins by selecting the three dots symbol in the top right corner of WhatsApp and choosing ‘Group info’ scrolling down to the member list, tapping on any member and selecting ‘Make group admin’. 

### How can you delete locations that have been shared? 

In WhatsApp within 60 hours of posting, the sharer of a location can long press the location share in WhatsApp > Select the bin icon along the top and select ‘Delete for everyone’. This will then be reflected in ChatMap as long as the chat is exported after the deletions have been made. In the final map the location will completely disappear. 

We recommend deleting the associated content with the location that is being deleted, otherwise this may inadvertently attach old content to a new location that is shared later by the same contact. 

Group admins can delete locations from anyone in the group within 60 hours of posting and this will also be reflected in ChatMap. 

You can also delete points in the ChatMap UI, those points won't be exported.

### Can group members replace/edit information that they have shared?

In WhatsApp, text can be edited up to 15 minutes after it has been added. This will be reflected in the map results with the edited message and a <This message was edited> string attached. 

### What happens if several people are messaging at the same time?

ChatMap matches the contact that has shared their location, with the same contact that has shared some content. So if someone else shares a piece of text just after you have shared your location it will not associate that other person's piece of text with your location. 

### What happens if a location is shared with no content?

This will create a point on the final map, but it will simply contain a URL with the coordinates and no other content. 

### Can the group channel be used for ‘general talk’? 

Yes, however if there is a lot of discussion this may confuse attempts to create location-based content. If you expect a lot of discussion consider setting up a separate group for questions and general communication. 

### Does it work offline? 

Yes, but not always, it can fail when people share several locations + messages. We recommend to not trust this option yet.

### How can I access the map data? 

After uploading the exported WhatsApp zip file to https://chatmap.hotosm.org/ select download. 

How to work with a group of people on various themes (urban issue, environmental issue, disaster risks, narratives and history, etc).

We recommend setting up separate group cats IF the people participating are different. If it is the same people, it is not recommended, but in the same chat, establish a code: instruct that the descriptive text of the marker starts with a pre-established category word, example:

* Environment: sick tree
* Environment: rubbish
* Environment: contaminated water
* Construction: vulnerable housing
* Construction: dangerous bridge
* Security: safe spot

If auth + live mode is enabled, you can log in and see your map, or open the shared link (which can be public or private).

### What is the maximum amount of time that you can wait between sharing your location and the content? 

There’s no max time, but it’s recommended to do both things at the same time.

### How should I share instructions to the group members?

As a message in the group, with a banner, video, webpage … any way you like really.

### What is the maximum length of text message that can be added? 

There’s no max length, the only limit is the WhatsApp one, and this is over 65 thousand characters.

Is there a limit to the number of messages in a group chat that can be mapped

The export limit for a WhatsApp group chat is 10,000 messages, this means that exported group chats with more than 10,000 messages will not include all the data, therefore any map created from that export with ChatMap will not be complete. 

---

_Thanks Sam Colchester for helping writing this document!_
