import React from "react";
import { FormattedMessage } from 'react-intl';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';

/**
 *
 * @param {object} data Chat data
 * @param {object} dataFiles Files data
 * Create a zip with chat data and files inside. Fire an
 * event for user to download the file
 */
function createAndDownloadZip(data, dataFiles) {
  const zip = new JSZip();

  // Get a list of media files from GeoJSON data
  const media_files = data.features.map(x => x.properties.file);

  // Add GeoJSON data to the zip file
  const geoJsonBlob = new Blob([JSON.stringify(data)], { type: 'application/json' });
  zip.file('data.geojson', geoJsonBlob);

  // Add each blob file to the zip file
  if (dataFiles) {
    for (const [filename, blob] of Object.entries(dataFiles)) {
      if (media_files.indexOf(filename) > -1) {
        zip.file(filename, blob);
      }
    }
  }

  // Generate the zip file and trigger the download
  zip.generateAsync({ type: 'blob' }).then((content) => {
    saveAs(content, `chatmap-${Math.floor(10000 + Math.random() * 90000)}.zip`);
  });
}

function SaveButton({ data, dataFiles }) {

  const handleClick = () => {
    createAndDownloadZip(data, dataFiles);
  };

  return (
    <button className="primaryButton" onClick={handleClick}>
      <FormattedMessage
        id = "app.download"
        defaultMessage="Download"
      />
    </button>
  );
}

export default SaveButton;
