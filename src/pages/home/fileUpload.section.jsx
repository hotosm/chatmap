import React from 'react';
import FileUpload from '../../components/FileUpload';

export default function FileUploadSection({
    handleDataFile,
    handleFiles
  }) {

  return (
    <>
      <div className="fileUpload">
        <FileUpload onDataFileLoad={handleDataFile} onFilesLoad={handleFiles} />
      </div>
    </>
  );
};