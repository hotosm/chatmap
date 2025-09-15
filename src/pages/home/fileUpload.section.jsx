import FileUpload from '../../components/FileUpload';

export default function FileUploadSection({
    handleDataFile,
    handleFiles,
    handleMediaOnlyChange,
    mediaOnly,
    onError,
  }) {

  return (
    <>
      <div className="fileUpload">
        <FileUpload
          onDataFileLoad={handleDataFile}
          onFilesLoad={handleFiles}
          onError={onError}
          mediaOnly={mediaOnly}
          onMediaOnlyChange={handleMediaOnlyChange}
        />
      </div>
    </>
  );
};