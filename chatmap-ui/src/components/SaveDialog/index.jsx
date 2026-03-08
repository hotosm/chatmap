import { useState, useCallback } from "react";
import { FormattedMessage } from "react-intl";
import { useNavigate } from "react-router";

import SlDialog from "@shoelace-style/shoelace/dist/react/dialog/index.js";
import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";
import SlTextarea from "@shoelace-style/shoelace/dist/react/textarea/index.js";
import { serialize } from '@shoelace-style/shoelace/dist/utilities/form.js';
import { useConfigContext } from "../../context/ConfigContext";

export default function SaveDialog({
  open, setOpen, data,
}) {
  const navigate = useNavigate();
  const { config } = useConfigContext();

  const [error, setError] = useState();

  const handleSubmit = useCallback(async (event) => {
    event.preventDefault();

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
      setError("There was an error saving the map");
    }
  }, [data]);

  return (
    <SlDialog
      open={open}
      onSlAfterHide={() => setOpen(false)}
    >
      <h2 slot="label" className="dialog__title">
        <FormattedMessage id="app.home.saveYourMap" defaultMessage="Save your map" />
      </h2>

      { error }

      <form onSubmit={handleSubmit}>
        <SlInput
          name="name"
          label="Write a name for it"
          placeholder="Ex: My community map"
          required
        />

        <SlTextarea
          name="description"
          label="What is this map about?"
          placeholder="You can use markdown"
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
