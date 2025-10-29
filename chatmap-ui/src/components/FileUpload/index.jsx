import { useState, useEffect, useRef } from "react";
import { FileUploader } from "react-drag-drop-files";
import JSZip from "jszip";
import { useIntl } from 'react-intl';
import { FormattedMessage } from 'react-intl';

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
const FileUpload = ({ onFilesLoad, onDataFileLoad, onError, mediaOnly, onMediaOnlyChange}) => {
  const [files, setFiles] = useState();
  const [loadedFilesCount, setLoadedFilesCount] = useState(0);
  const [filesCount, setFilesCount] = useState(0);
  const [zipFilesCount, setZipFilesCount] = useState(0);
  const [loadedZipFilesCount, setLoadedZipFilesCount] = useState(0);
  const mediaOnlySwitchRef = useRef();
  const intl = useIntl();

  // Handle media only switch change event
  useEffect(() => {
    const mediaOnlyEl = mediaOnlySwitchRef.current;
    if (!mediaOnlyEl) return;
    mediaOnlyEl.addEventListener("sl-change", onMediaOnlyChange);
    return () => {
      mediaOnlyEl.removeEventListener("sl-change", onMediaOnlyChange);
    };
  }, []);

  const handleChange = (loadedFiles) => {
    setZipFilesCount(loadedFiles.length);
    for (let i = 0; i < loadedFiles.length; i++) {

      // Get file object
      const file = loadedFiles[i];
      const fileFormat = getFileFormat(file.name);

      // The chat was exported as a .zip file
      if (fileFormat === "zip") {
        // Un-compress file
        new JSZip().loadAsync( file )
        .then(function(zip) {
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
      if (files) {
        onFilesLoad(files);
      } else {
        onError && onError();
      }
    }
  }, [files, filesCount, loadedFilesCount, loadedZipFilesCount, onFilesLoad]);

  const loading = filesCount != loadedFilesCount;

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
            <sl-button
              className="fileUploadDropArea"
              size="large"
            >
              <sl-icon name="file-arrow-up-fill" slot="prefix"></sl-icon>
              <FormattedMessage
                id = "app.uploadLabel"
                defaultMessage="Upload your .zip file here"
              />
            </sl-button>}
        />
      </div>
      <div className="fileUploadOptions">
        <sl-switch
          size="small"
          checked={mediaOnly && "checked"}
          ref={mediaOnlySwitchRef}
        >
          <FormattedMessage
            id = "app.mediaOnly"
            defaultMessage="Add only media files to the map (no text)"
          />
        </sl-switch>
      </div>

    </>
  );
}

export default FileUpload;
