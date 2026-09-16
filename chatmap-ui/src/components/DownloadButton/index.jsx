import { FormattedMessage } from 'react-intl';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import { hashUsernames } from "../ChatMap/hash";

const isValidDate = d => (
  d instanceof Date && !isNaN(d)
)

export const processChatData = async (chatmapId, data) => {
  
  const usernames = data.features.reduce((accumulator, feature) => {
    accumulator[feature.properties.username] = ""
    return accumulator;
  }, {});

 
  const usernames_hashes = await hashUsernames(usernames);

  let newData = {
    _chatmapId: chatmapId,
    ...data,
    features:
      data.features
        .filter(feature => !feature.properties.removed)
        .map(feature => {
          feature.properties.username = usernames_hashes[feature.properties.username];
          delete feature.properties.timeString;
          return feature;
        })
  };

  return newData;
};

/**
 *
 * @param {object} data Chat data
 * @param {object} dataFiles Files data
 * Create a zip with chat data and files inside. Fire an
 * event for user to download the file
 */
const createAndDownloadZip = async (data, dataFiles, getDataFiles) => {
  const zip = new JSZip();

  // The name of the file to save
  const chatmapId = data._chatmapId;

  // Add GeoJSON data to the zip file
  let newData = await processChatData(chatmapId, data);

  // Get a list of media files from GeoJSON data
  const media_files = newData.features.map(x => x.properties.file);

  const geoJsonBlob = new Blob([JSON.stringify(newData)], { type: 'application/json' });
  zip.file('data.geojson', geoJsonBlob);

  // Add each blob file to the zip file
  const _dataFiles = dataFiles || await getDataFiles();
  if (_dataFiles) {
    for (const [filename, blob] of Object.entries(_dataFiles)) {
      console.log(filename, blob)
      if (media_files.indexOf(filename) > -1) {
        zip.file(filename, blob);
      }
    }
  }

  // Generate the zip file and trigger the download
  zip.generateAsync({ type: 'blob' }).then((content) => {
    saveAs(content, `chatmap-${chatmapId}.zip`);
  });
}

function DownloadButton({ data, dataFiles, getDataFiles, url, className, disabled, format, label, variant}) {

  const handleClick = () => {
    if (url) {
      window.open(url);
    } else {
      createAndDownloadZip(data, dataFiles, getDataFiles);
    }
  };

  return (
    <sl-button
      disabled={disabled}
      className={className}
      variant={variant || "default"}
      outline
      size="small"
      onClick={handleClick}
    >
      {label ? label : <FormattedMessage
        id = "app.download"
        defaultMessage="Download"
      />} {format && `(${format})`}
      <sl-icon name="save2" slot="prefix"></sl-icon>
    </sl-button>
  );
}

export default DownloadButton;
