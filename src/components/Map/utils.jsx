/*
* Utility functions
*/

/**
 *
 * @param {object} properties Message properties
 * @returns {string} A formatted and padded datetime, ex: 02:15
 */
export const formatDate = (properties) => {
  const d = new Date(properties.time);
  return (
    String(d.getHours()).padStart(2, '0') + ":" +
    String(d.getMinutes()).padStart(2, '0'))
};

/**
 *
 * @param {object} properties Properties object for the message
 * @param {object} dataFiles Files with data
 * @returns {string} Message (text message or HTML for image, video)
 */
export const getMessage = (properties, dataFiles) => {
  if (properties.file && dataFiles && properties.file in dataFiles) {
    if (properties.file.endsWith("jpg") || properties.file.endsWith("jpeg")) {
      const url = URL.createObjectURL(dataFiles[properties.file]);
      return <a href={url} target="_blank"><img className="popupImage" alt="Message attached file" src={url} /></a>
    } else if (properties.file.endsWith("mp4")) {
      return <video controls autoplay loop className="popupImage" alt="Message attached file" src={URL.createObjectURL(dataFiles[properties.file])} />
    }
  }
  return properties.message;
}