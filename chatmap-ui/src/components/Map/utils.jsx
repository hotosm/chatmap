import { FormattedMessage } from "react-intl";
/*
* Utility functions
*/

/**
 *
 * @param {string} datetime An ISO datetime
 * @returns {string} A formatted and padded datetime, ex: 02:15:22
 */
export const formatDate = (datetime) => {
  const d = new Date(datetime);

  if (isNaN(d.getTime())) {
    return ""; // Something went wrong with datetime parsing
  }

  return new Intl.DateTimeFormat(undefined, {
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
    timeZone: new Intl.DateTimeFormat().resolvedOptions().timeZone
  }).format(d).replace(/,/g, '');
};

/**
 *
 * @param {object} message Properties object for the message
 * @param {object} dataFiles Files with data
 * @returns {string} Message (text message or HTML for image, video)
 */
export function GetMessage({message, msgType, dataFiles}) {
  let content;
  if (message.file && dataFiles && message.file in dataFiles) {

    // Image
    if (msgType === "image") {
      const url = URL.createObjectURL(dataFiles[message.file]);
      content = <img className="popupImage" alt={message.file} src={url} />

    // Video
    } else if (msgType === "video") {
      content = <video controls className="popupVideo" alt={message.file} src={URL.createObjectURL(dataFiles[message.file])} />

    // Audio
    } else if (msgType === "audio") {
      content = <audio controls className="popupAudio" alt={message.file} src={URL.createObjectURL(dataFiles[message.file])} />
    }
  } else if (message.file && message.file.startsWith("http")) {
    if (message.file.endsWith("jpg")) {
      content = <img className="popupImage" alt={message.file} src={message.file} />;
    } else if (message.file.endsWith("mp4")) {
      content = <video controls className="popupVideo" alt={message.file} src={message.file} />
    } else if (message.file.endsWith("opus")) {
      content = <audio controls className="popupAudio" alt={message.file} src={message.file} />
    }
  }

  return <>
    {/* Media */}
    <div className="media">
      { content ? content : null }
    </div>
    {/* Text */}
    { message.message && message.message !== " " ?
      <p className="text">{message.message}</p> : (!content ?
        <p className="text location-only">
          <FormattedMessage id="app.map.locationOnly" defaultMessage="Location only" />
        </p>
      : null)
    }
  </>;
};
