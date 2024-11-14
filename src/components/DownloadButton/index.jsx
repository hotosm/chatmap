import React from "react";
import { FormattedMessage } from 'react-intl';

function DownloadButton({ data, filename }) {

  const createDownloadLink = (data) => (
    "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data))
  )

  return (
    <a className="primaryButton" href={createDownloadLink(data)} download={`${filename}.geojson`}>
      <FormattedMessage
        id = "app.download"
        defaultMessage="Download"
      />
    </a>
  );
}

export default DownloadButton;
