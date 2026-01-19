import { useState, useEffect } from "react";
import { FileUploader } from "react-drag-drop-files";
import JSZip from "jszip";
import { useIntl } from 'react-intl';
import { FormattedMessage } from 'react-intl';

// Accepted file types
const fileTypes = ["zip"];

// Get file format: "chat", "zip" or "media"
const getFileFormat = (filename) => {
  // Get file format from file extension
  const fileName = filename.toLowerCase();
  if (fileName.endsWith(".txt") || fileName.endsWith(".json") || fileName.endsWith(".geojson")) {
    return "chat";
  } else if (fileName.endsWith(".zip")) {
    return "zip";
  } else if (
    fileName.endsWith(".jpg") ||
    fileName.endsWith(".jpeg") ||
    fileName.endsWith(".mp4") ||
    fileName.endsWith(".ogg") ||
    fileName.endsWith(".opus") ||
    fileName.endsWith(".mp3") ||
    fileName.endsWith(".m4a") ||
    fileName.endsWith(".wav")
  ) {
    return "media";
  }
}

// Upload a file to the app
// It shows an upload area, reacts when files are uploaded.
// It can manage all file formats ("chat", "zip" or "media")
const FileUpload = ({ onFilesLoad, onDataFileLoad, onError}) => {
  const [files, setFiles] = useState();
  const [loadedFilesCount, setLoadedFilesCount] = useState(0);
  const [filesCount, setFilesCount] = useState(0);
  const [zipFilesCount, setZipFilesCount] = useState(0);
  const [loadedZipFilesCount, setLoadedZipFilesCount] = useState(0);
  const intl = useIntl();

  const handleChange = (loadedFiles) => {
    setZipFilesCount(loadedFiles.length);

    for (const file of loadedFiles) {
      // Get file object
      const fileFormat = getFileFormat(file.name);

      // The chat was exported as a .zip file
      if (fileFormat === "zip") {
        // Un-compress file
        new JSZip().loadAsync(file)
          .then((zip) => {
            setFilesCount(prev => prev += Object.keys(zip.files).length);

            Object.keys(zip.files).forEach(filename => {
              // Process each file, depending on the file format
              const fileFormat = getFileFormat(filename);

              // Chat files
              if (fileFormat === "chat") {
                zip.files[filename].async("string").then(function (data) {
                  setFiles(prevFiles => (
                    {...prevFiles, ...{[file.name]: data}}
                  ));
                  // Keeps loaded file count
                  setLoadedFilesCount(prev => prev+=1);
                });
              // Media files (jpg, jpeg, mp4 and audio files)
              } else if (fileFormat === "media") {
                zip.files[filename].async("arraybuffer").then(function (data) {
                  const buffer = new Uint8Array(data);
                  const blob = new Blob([buffer.buffer]);
                  onDataFileLoad(filename, blob)
                  // Keeps loaded file count
                  setLoadedFilesCount(prev => prev+=1);
                });
              } else {
                // Keeps loaded file count
                setLoadedFilesCount(prev => prev+=1);
              }
            })
          });

        setLoadedZipFilesCount(prev => prev+=1);
      }
    };
  };

  // All files are loaded into memory.
  useEffect(() => {
    if (filesCount > 0 && filesCount === loadedFilesCount &&
        files && zipFilesCount === Object.keys(files).length
    ) {
      onFilesLoad(files);
    }
  }, [files, filesCount, loadedFilesCount, loadedZipFilesCount, onFilesLoad]);

  const loading = filesCount != loadedFilesCount;

  const hoverTitle = intl.formatMessage({
    id: "app.home.dropHere",
    defaultMessage: "Drop your zip file here",
  });

  return (
    <>
      {/* Loading message */}
    { loading ?
      <div className="loadingMessage">
        <p style={{"textAlign": "center"}}>
          {intl.formatMessage({
            id: "app.loading",
            defaultMessage: "Loading"
            })} ({loadedFilesCount} / {filesCount})...
          </p>
          <sl-progress-bar value={(loadedFilesCount * 100) / filesCount}></sl-progress-bar>
      </div>
      : ""}

      {/* File upload area */}
      <div className="fileUploadWrapper" style={loading ? {display: "none"} : null}>
        <FileUploader
          handleChange={handleChange}
          multiple
          types={fileTypes}
          name="file"
          classes="fileUploadMain"
          children={
            <sl-button size="large" className="featured">
              <sl-icon slot="prefix" name="file-earmark-plus-fill"></sl-icon>
              <FormattedMessage id="app.home.openChatExport" defaultMessage="Open your chat export" />
            </sl-button>
          }
          dropMessageStyle={{height: "100%"}}
          hoverTitle={hoverTitle}
        />
      </div>
    </>
  );
}

export default FileUpload;
