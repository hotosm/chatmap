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
  const newData = {
    ...data
  }

  newData.features.forEach(feature => {
    // Delete username for enhanced privacy and security
    delete feature.properties.username;

    // Delete unused properties
    delete feature.properties.timeString;
    delete feature.properties.related;

    if (feature.properties.tags) {
      // Convert tags object to string
      // Ex: { building: yes } to "building_yes"
      feature.properties.tags = feature.properties.tags.join(",");
    }
  })
  const geoJsonBlob = new Blob([JSON.stringify(newData)], { type: 'application/json' });
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
    <sl-button
      variant="primary"
      onClick={handleClick}
    >
      <FormattedMessage
        id = "app.download"
        defaultMessage="Download"
      />
      <sl-icon name="save2" slot="prefix"></sl-icon>
    </sl-button>
  );
}

export default SaveButton;
