/*
* Utility functions
*/

/**
 *
 * @param {object} properties Message properties
 * @param {string} properties Message type
 * @returns {string} A formatted and padded datetime, ex: 02:15:22
 */
export const formatDate = (time) => {
  const d = new Date(time);

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(d);
};

/**
 *
 * @param {object} message Properties object for the message
 * @param {object} dataFiles Files with data
 * @returns {string} Message (text message or HTML for image, video)
 */
export const getMessage = (message, msgType, dataFiles) => {
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
  } else if (message.file && message.file.startsWith("http") && message.file.endsWith("jpg")) {
    content = <img className="popupImage" alt={message.file} src={message.file} />;
  }

  return <>
      {/* Media */}
      <div className="media">
      { content ? content : null }
      </div>
      {/* Text */}
      { message.message && message.message !== " " ?
      <p className="text">{message.message}</p> : null}
    </>
}
