import { useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";
import { useNavigate } from "react-router";

import SlDialog from "@shoelace-style/shoelace/dist/react/dialog/index.js";
import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";
import SlTextarea from "@shoelace-style/shoelace/dist/react/textarea/index.js";
import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';

import { serialize } from '@shoelace-style/shoelace/dist/utilities/form.js';
import { useConfigContext } from "../../context/ConfigContext";

export default function EditMapDialog({
  open, setOpen, mapData, onSuccess
}) {

  const navigate = useNavigate();
  const { config } = useConfigContext();
  const intl = useIntl();

  const [error, setError] = useState();
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      // This has to happen before setLoading(true) because that call makes the
      // for disapear from the DOM, this returning an empty object.
      const formData = serialize(event.target);
      setLoading(true);

      const response = await fetch(`${config.API_URL}/map/${mapData.id}`, {
        method: "PUT",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error("Your map contains errors that prevent it from saving");
      } else{
        setLoading(false);
        setOpen(false);
        onSuccess && onSuccess(await response.json())
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
        <FormattedMessage id="app.home.editMap" defaultMessage="Edit map" />
      </h2>

      <div className="error error-box">
        { error }
      </div>

      { loading ? <>
      ...
      </> : <>
        <form onSubmit={handleSubmit}>
          <SlInput
            name="name"
            label={intl.formatMessage({id: "app.save.name", defaultMessage: "Write a name for it"})}
            placeholder={intl.formatMessage({id: "app.save.namePlaceholder", defaultMessage: "Ex: My community map"})}
            required
            value={mapData.name}
          />

          <SlTextarea
            name="description"
            label={intl.formatMessage({id: "app.save.description", defaultMessage: "What is this map about?"})}
            placeholder=""
            value={mapData.description}
          />

          <SlButton type="submit" variant="primary" className="dialog__btn dark-btn">
            <FormattedMessage
              id="app.home.editDialog.save"
              defaultMessage="Save"
            />
          </SlButton>
        </form>
      </>}
    </SlDialog>
  );
};
