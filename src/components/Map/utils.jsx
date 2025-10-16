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
  return (
    `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
  )
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
      const urlParams = new URLSearchParams(url.split("?")[1]);
      const phoneNumber = urlParams.get("user");
      const hash = phoneNumber ? btoa(phoneNumber) : "unknown";
      const urlWithHash = url.replace(/user=([^&]*)/, 'h=' + hash);
      content = <img className="popupImage" alt="Message attached file" src={urlWithHash} />

    // Video
    } else if (msgType === "video") {
      content = <video controls className="popupVideo" alt="Message attached file" src={URL.createObjectURL(dataFiles[message.file])} />

    // Audio
    } else if (msgType === "audio") {
      content = <audio controls className="popupAudio" src={URL.createObjectURL(dataFiles[message.file])} />
    }
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