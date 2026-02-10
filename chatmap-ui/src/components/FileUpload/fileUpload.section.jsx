import FileUpload from '../../components/FileUpload';

export default function FileUploadSection({
    handleDataFile,
    handleFiles,
    onError,
  }) {

  return (
    <>
      <div className="fileUpload">
        <FileUpload
          onDataFileLoad={handleDataFile}
          onFilesLoad={handleFiles}
          onError={onError}
        />
      </div>
    </>
  );
};
