import FileUpload from '../../components/FileUpload';
import { FormattedMessage } from "react-intl";

export default function FileUploadSection({
    handleDataFile,
    handleFiles,
    onError,
  }) {

  return (
    <>
      <p className="home__subtitle"><FormattedMessage id="app.home.subtitle" defaultMessage="Convert your chats into maps."/></p>
      <FileUpload
        onFilesLoad={handleFiles}
        onDataFileLoad={handleDataFile}
        onError={onError}
      />
      <p className="home__note">
        <FormattedMessage id="app.home.itWorks" defaultMessage="It works with WhatsApp, Telegram or Signal" />
        {/* <sl-icon-button name="plus-circle-dotted" /> */}
      </p>
    </>
  );
};