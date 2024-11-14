import React, { useState, useEffect } from "react";
import { FileUploader } from "react-drag-drop-files";
import JSZip from "jszip";
import { useIntl } from 'react-intl';

const fileTypes = ["txt", "zip"];

function FileUpload({ onFileLoad, onDataFileLoad, onError}) {
  const [file, setFile] = useState(null);
  const intl = useIntl();

  const handleChange = (file) => {
    // Read a .txt export
    if (file.name.toLowerCase().endsWith(".txt")) {
      setFile(file);
    } else {
      // File is a Zip
      new JSZip().loadAsync( file )
      .then(function(zip) {
        Object.keys(zip.files).forEach(filename => {
          if (filename.toLowerCase().endsWith(".txt")) {
            zip.files[filename].async("string").then(function (data) {
              onFileLoad(data);
            });
          } else if (filename.toLowerCase().endsWith(".jpg")) {
            zip.files[filename].async("arraybuffer").then(function (data) {
              const buffer = new Uint8Array(data);
              const blob = new Blob([buffer.buffer]);
              onDataFileLoad(filename, blob);
            });
          }
        })
      });
    }
  };

  useEffect(() => {
    if (file) {
      var reader = new FileReader();
      reader.readAsText(file, "UTF-8");
      reader.onload = function (evt) {
        onFileLoad(evt.target.result)
      }
      reader.onerror = function (evt) {
        onError();
      }
    }
  }, [file, onError, onFileLoad]);

  return (
    <FileUploader
      classes={"fileUploadDropArea"}
      handleChange={handleChange}
      name="file"
      types={fileTypes}
      label={intl.formatMessage({id: "app.uploadLabel", defaultMessage: "Upload or drag a file right here"})}
    />
  );
}

export default FileUpload;
