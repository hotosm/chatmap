import { FormattedMessage } from 'react-intl';

export default function NoLocationsSection({ handleNewUploadClick }) {
  const mailLink = `mailto:emilio.mariscal@hotosm.org?subject=ChatMap Error&body=Hi, something went wrong with chatmap, my chat contains locations but is not working.`
  return (
    <div className="errorMessage noLocations">
      <header className="header">
        <h1 class="iconTitle">
          <sl-icon name="search-heart"></sl-icon>
        </h1>
        <h2>
          No locations found in this file
        </h2>
        <h3>The chat that you've uploaded doesn't seems to contain any location.</h3>
      </header>
      <div className="buttons">
        <sl-button
          onClick={handleNewUploadClick}
          variant="success"
        >
          <sl-icon name="arrow-clockwise" slot="prefix"></sl-icon>
          <FormattedMessage
            id = "app.uploadNewFile"
            defaultMessage="Upload new file"
          />
        </sl-button>
      </div>
      <div>
        <p>
              If you are sure that at least one location was shared in this chat,
              please let us know to <a href={mailLink}>emilio.mariscal@hotosm.org</a>
          <br /><br />or create an issue in <a href="https://github.com/hotosm/chatmap/issues">github.com/hotosm/chatmap/issues</a>
        </p>
      </div>
    </div>
  );
};