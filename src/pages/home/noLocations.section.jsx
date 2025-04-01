import React from 'react';
import { FormattedMessage } from 'react-intl';

export default function FileUploadSection({ handleNewUploadClick }) {
  return (
    <>
      <h2>
        <FormattedMessage
          id = "app.nolocations"
          defaultMessage="No locations found in this file"
        />
      </h2>
      <button onClick={handleNewUploadClick} className="secondaryButton">
      <FormattedMessage
          id = "app.uploadNewFile"
          defaultMessage="Upload new file"
        /> 
      </button>
  </>
  );
};