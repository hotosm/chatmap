import { useState, useCallback, useEffect } from "react";
import { FormattedMessage, useIntl } from "react-intl";
import { useNavigate } from "react-router";

import SlDialog from "@shoelace-style/shoelace/dist/react/dialog/index.js";
import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";
import SlTextarea from "@shoelace-style/shoelace/dist/react/textarea/index.js";
import { serialize } from '@shoelace-style/shoelace/dist/utilities/form.js';
import { useConfigContext } from "../../context/ConfigContext";

export default function SaveDialog({
  open, setOpen, data, dataFiles,
}) {
  const navigate = useNavigate();
  const { config } = useConfigContext();
  const intl = useIntl();

  const [error, setError] = useState();

  async function handleSubmit(event) {
    event.preventDefault();

    const mediaFiles = data.features
      .filter(f => !f.properties.removed && f.properties.file)
      .map(f => f.properties.file);
    const allFiles = Object.entries(dataFiles).filter(([filename, blob]) => {
      return mediaFiles.indexOf(filename) > -1;
    });

    try {
      for (let [filename, blob] of allFiles) {
        const formData = new FormData();
        formData.append("file", blob, filename);
        const mediaResponse = await fetch(`${config.API_URL}/map/media`, {
          method: "POST",
          credentials: "include",
          body: formData,
        });

        if (!mediaResponse.ok) {
          throw new Error(`Error saving media ${filename}`);
        }
      }

      const response = await fetch(`${config.API_URL}/map`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({...data, ...serialize(event.target)}),
      });

      if (response.ok) {
        navigate('/maps');
      } else {
        throw new Error("Your map contains errors that prevent it from saving");
      }
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <SlDialog
      open={open}
      onSlAfterHide={() => setOpen(false)}
    >
      <h2 slot="label" className="dialog__title">
        <FormattedMessage id="app.home.saveYourMap" defaultMessage="Save your map" />
      </h2>

      <div className="error error-box">
        { error }
      </div>

      <form onSubmit={handleSubmit}>
        <SlInput
          name="name"
          label={intl.formatMessage({id: "app.save.name", defaultMessage: "Write a name for it"})}
          placeholder={intl.formatMessage({id: "app.save.namePlaceholder", defaultMessage: "Ex: My community map"})}
          required
        />

        <SlTextarea
          name="description"
          label={intl.formatMessage({id: "app.save.description", defaultMessage: "What is this map about?"})}
          placeholder={intl.formatMessage({id: "app.save.descriptionPlaceholder", defaultMessage: "You can use markdown"})}
        />

        <sl-button type="submit" slot="footer" variant="primary" className="dialog__btn dark-btn">
          <FormattedMessage
            id="app.home.dialog.continue"
            defaultMessage="Continue"
          />
        </sl-button>
      </form>
    </SlDialog>
  );
};
