import { useState } from "react";
import { FileUploader } from "react-drag-drop-files";
import JSZip from "jszip";
import { useIntl } from 'react-intl';

// Accepted file types
const fileTypes = ["zip"];

// Get file format: "chat", "zip" or "media"
const getFileFormat = (filename) => {
  // Ignore MacOS system files
  if (filename.substring(0, 8) === "__MACOSX") {
    return;
  }
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
const FileUpload = ({ onFilesLoad, onDataFileLoad, children}) => {
  const [loadedFilesCount, setLoadedFilesCount] = useState(0);
  const [filesCount, setFilesCount] = useState(0);
  const intl = useIntl();

  const handleChange = (loadedFiles) => {
    setFilesCount(loadedFiles.length);
    setLoadedFilesCount(0);

    Promise.all(Array.from(loadedFiles).map((file) => {
      return new Promise((resolve, reject) => {
        const fileFormat = getFileFormat(file.name);

        // The chat was exported as a .zip file
        if (fileFormat === "zip") {
          // Un-compress file
          new JSZip().loadAsync( file )
          .then(function(zip) {
            Object.keys(zip.files).forEach(filename => {
              // Process each file, depending on the file format
              const fileFormat = getFileFormat(filename);
              // Chat files
              if (fileFormat === "chat") {
                zip.files[filename].async("string").then(function (data) {
                  setLoadedFilesCount((prev) => prev + 1);
                  resolve({[file.name]: data});
                });
              } else if (fileFormat === "media") {
                // Media files (jpg, jpeg, mp4 and audio files)
                zip.files[filename].async("arraybuffer").then(function (data) {
                  const buffer = new Uint8Array(data);
                  const blob = new Blob([buffer.buffer]);
                  onDataFileLoad(filename, blob)
                });
              }
            });
          });
        }
      });
    })).then((files) => {
      onFilesLoad(files.reduce((acc, cur) => ({...acc, ...cur})));
    });
  };

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
          dropMessageStyle={{
            backgroundColor: "var(--hot-color-neutral-0)",
            fontSize: "var(--hot-font-size-medium)",
            fontWeight: "bold"
          }}
          hoverTitle={hoverTitle}
        >
          { children }
        </FileUploader>
      </div>
    </>
  );
}

export default FileUpload;
