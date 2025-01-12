import React, { useState, useEffect } from "react";
import { FileUploader } from "react-drag-drop-files";
import JSZip from "jszip";
import { useIntl } from 'react-intl';

function stripPath(filename) {
  return filename.substring(filename.lastIndexOf("/") + 1, filename.length);
}

const fileTypes = ["txt", "zip", "json"];

const getFileFormat = (filename) => {
  // Ignore MacOS system files
  if (filename.substring(0, 8) === "__MACOSX") {
      return;
  }
  const fileName = filename.toLowerCase();
  if (fileName.endsWith(".txt") || fileName.endsWith(".json")) {
    return "chat";
  } else if (fileName.endsWith(".zip")) {
    return "zip";
  } else if (fileName.endsWith(".jpg") || fileName.endsWith(".jpeg") || fileName.endsWith(".mp4")) {
    return "media";
  }
}

const FileUpload = ({ onFilesLoad, onDataFileLoad, onError}) => {
  const [files, setFiles] = useState();
  const [filesCount, setFilesCount] = useState();
  const intl = useIntl();

  const handleChange = (loadedFiles) => {
    setFilesCount(loadedFiles.length);
    for (let i = 0; i < loadedFiles.length; i++) {
      const file = loadedFiles[i];
      const fileFormat = getFileFormat(file.name); 

      // Read a text or JSON export
      if (fileFormat === "chat") {
        var reader = new FileReader();
          reader.readAsText(file, "UTF-8");
          reader.onload = function (evt) {
            setFiles(prevFiles => (
              {...prevFiles, ...{[file.name]: evt.target.result}}
            ));
          }
          reader.onerror = function (evt) {
            onError(file.name);
          }

      // Read a Zip export
      } else if (fileFormat === "zip") {
        new JSZip().loadAsync( file )
        .then(function(zip) {
          Object.keys(zip.files).forEach(filename => {
            const fileFormat = getFileFormat(filename); 
            if (fileFormat === "chat") {
              zip.files[filename].async("string").then(function (data) {
                setFiles(prevFiles => (
                  {...prevFiles, ...{[file.name]: data}}
                ));
              });
            } else if (fileFormat === "media") {
              zip.files[filename].async("arraybuffer").then(function (data) {
                const buffer = new Uint8Array(data);
                const blob = new Blob([buffer.buffer]);
                onDataFileLoad(filename, blob)
              });
            }
          })
        });
      }
    };
  };

  useEffect(() => {
    if (files && Object.keys(files).length === filesCount) {
      onFilesLoad(files);
    }
  }, [files, onFilesLoad]);

  const loading = files && Object.keys(files).length !== filesCount;

  return (
    <>
    { loading ? <p style={{"textAlign": "center"}}>
      {intl.formatMessage({id: "app.loading", defaultMessage: "Loading"})} ...
    </p> : ""}
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
