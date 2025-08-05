import { useState, useEffect } from "react";
import { FileUploader } from "react-drag-drop-files";
import JSZip from "jszip";
import { useIntl } from 'react-intl';

// Accepted file types
const fileTypes = ["txt", "zip", "json"];

// Get file format: "chat", "zip" or "media"
const getFileFormat = (filename) => {
  // Ignore MacOS system files
  if (filename.substring(0, 8) === "__MACOSX") {
    return;
  }
  // Get file format from file extension
  const fileName = filename.toLowerCase();
  if (fileName.endsWith(".txt") || fileName.endsWith(".json")) {
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
  const intl = useIntl();

  const handleChange = (loadedFiles) => {
    for (let i = 0; i < loadedFiles.length; i++) {

      // Get file object
      const file = loadedFiles[i];
      const fileFormat = getFileFormat(file.name);

      // The chat was exported as a single text or JSON file
      if (fileFormat === "chat") {
        var reader = new FileReader();
        reader.readAsText(file, "UTF-8");
        reader.onload = function (evt) {
          setFiles(prevFiles => (
              {...prevFiles, ...{[file.name]: evt.target.result}}
          ));
          // Keeps loaded file count
            setLoadedFilesCount(prev => prev+=1);
        }
        reader.onerror = function (evt) {
          onError(file.name);
        }

        // The chat was exported as a .zip file
      } else if (fileFormat === "zip") {
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
      }
    };
  };

  // All files are loaded into memory.
  useEffect(() => {
    if (filesCount > 0 && loadedFilesCount == filesCount) {
      if (files) {
        onFilesLoad(files);
      } else {
        onError && onError();
      }
    }
  }, [files, filesCount, loadedFilesCount, onFilesLoad]);

  const loading = filesCount != loadedFilesCount;

  return (
    <>
      {/* Loading message */}
    { loading ? <p style={{"textAlign": "center"}}>
      {intl.formatMessage({id: "app.loading", defaultMessage: "Loading"})} ({loadedFilesCount} / {filesCount})...
      </p> : ""}

      {/* File upload area */}
    <div style={loading ? {display: "none"} : null}>
        <FileUploader
          classes={"fileUploadDropArea"}
          handleChange={handleChange}
          multiple
          name="file"
          types={fileTypes}
      label={intl.formatMessage({id: "app.uploadLabel", defaultMessage: "Upload or drag a file right here"})}
        />
      </div>

    </>
  );
}

export default FileUpload;
