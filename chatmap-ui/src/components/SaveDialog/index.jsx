import { useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";
import { useNavigate } from "react-router";

import SlDialog from "@shoelace-style/shoelace/dist/react/dialog/index.js";
import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";
import SlTextarea from "@shoelace-style/shoelace/dist/react/textarea/index.js";
import SlProgressBar from '@shoelace-style/shoelace/dist/react/progress-bar/index.js';
import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';

import { serialize } from '@shoelace-style/shoelace/dist/utilities/form.js';
import { useConfigContext } from "../../context/ConfigContext";

export default function SaveDialog({
  open, setOpen, data, dataFiles
}) {

  console.log(data);
  const navigate = useNavigate();
  const { config } = useConfigContext();
  const intl = useIntl();

  const [error, setError] = useState();
  const [totalFiles, setTotalFiles] = useState(1);
  const [sentFiles, setSentFiles] = useState(0);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();

    const mediaFiles = data.features
      .filter(f => f.properties.file)
      .map(f => f.properties.file);
    const allFiles = Object.entries(dataFiles).filter(([filename, blob]) => {
      return mediaFiles.indexOf(filename) > -1;
    });

    // Simply to avoid a division by 0 problem in the case of no files
    setTotalFiles(allFiles.length + 1);

    try {
      // This has to happen before setLoading(true) because that call makes the
      // for disapear from the DOM, this returning an empty object.
      const formData = serialize(event.target);
      setLoading(true);

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

        const newFilename = (await mediaResponse.json()).uri;

        data.features.forEach((feature) => {
          if (feature.properties.file === filename) {
            feature.properties.file = newFilename;
          }
        });

        setSentFiles((value) => value + 1);
      }

      const response = await fetch(`${config.API_URL}/map`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({...data, ...formData}),
      });

      setSentFiles((value) => value + 1);

      if (response.ok) {
        navigate('/maps');
      } else {
        throw new Error("Your map contains errors that prevent it from saving");
      }
    } catch (e) {
      setError(e.message);
      setLoading(false);
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

      { loading ? <>
        <FormattedMessage id="app.save.uploading" defaultMessage="Uploading media..." />
        <SlProgressBar value={(sentFiles / totalFiles) * 100} />
      </> : <>
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

          <SlButton type="submit" variant="primary" className="dialog__btn dark-btn">
            <FormattedMessage
              id="app.home.saveDialog.continue"
              defaultMessage="Continue"
            />
          </SlButton>
        </form>
      </>}
    </SlDialog>
  );
};
