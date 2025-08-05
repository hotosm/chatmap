/*
* Utility functions
*/

/**
 *
 * @param {object} properties Message properties
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
 * @param {object} properties Properties object for the message
 * @param {object} dataFiles Files with data
 * @returns {string} Message (text message or HTML for image, video)
 */
export const getMessage = (properties, dataFiles) => {
  let content;
  if (properties.file && dataFiles && properties.file in dataFiles) {
    if (properties.file.endsWith("jpg") || properties.file.endsWith("jpeg")) {
      const url = URL.createObjectURL(dataFiles[properties.file]);
      content = <a href={url} target="_blank"><img className="popupImage" alt="Message attached file" src={url} /></a>
    } else if (properties.file.endsWith("mp4")) {
      content = <video controls className="popupImage" alt="Message attached file" src={URL.createObjectURL(dataFiles[properties.file])} />
    } else if (
      properties.file.endsWith("ogg") ||
      properties.file.endsWith("opus") ||
      properties.file.endsWith("mp3") ||
      properties.file.endsWith("m4a") ||
      properties.file.endsWith("wav")
    ) {
      content = <audio controls className="popupAudio" src={URL.createObjectURL(dataFiles[properties.file])} />
    }
  } else if (properties.file.indexOf(".jpg") > 0 ) {
      content = <a href={properties.file} target="_blank"><img className="popupImage" alt="Message attached file" src={properties.file} /></a>
  }
  return <>
      { content ? content : null }
      { properties.message ? <p className="text">{properties.message}</p> : null}
    </>
}