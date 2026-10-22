import { useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";
import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';
import SlRadioGroup from "@shoelace-style/shoelace/dist/react/radio-group/index.js";
import SlRadio from "@shoelace-style/shoelace/dist/react/radio/index.js";

/**
 * A key of the map: its name and, when it is new, whether a point takes one
 * value or many, and whether they are picked from a list or written. Those
 * two do not change once the key exists.
 */
export default function KeyForm({ keyItem, loading, onSave, onCancel }) {
  const intl = useIntl();
  const isNew = !keyItem.id;

  const [name, setName] = useState(keyItem.key || "");
  const [single, setSingle] = useState(keyItem.single ?? true);
  const [closed, setClosed] = useState(keyItem.closed ?? true);

  function handleSubmit(event) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    onSave(isNew ? { key: trimmed, single, closed, values: [] } : { key: trimmed });
  }

  return (
    <form onSubmit={handleSubmit}>
      <SlInput
        className="tags__input"
        required
        maxlength={40}
        value={name}
        label={intl.formatMessage({ id: "app.tags.keyLabel", defaultMessage: "Name" })}
        placeholder={intl.formatMessage({ id: "app.tags.keyPlaceholder", defaultMessage: "Ex: Status, Fuel, Category" })}
        onSlInput={(event) => setName(event.target.value)}
      />
      { isNew && <>
        <SlRadioGroup
          className="tags__input tags__choice"
          label={intl.formatMessage({ id: "app.tags.howMany", defaultMessage: "How many per point?" })}
          value={single ? "single" : "many"}
          onSlChange={(event) => setSingle(event.target.value === "single")}
        >
          <SlRadio value="single">
            <FormattedMessage id="app.tags.single" defaultMessage="One (ex: a status)" />
          </SlRadio>
          <SlRadio value="many">
            <FormattedMessage id="app.tags.many" defaultMessage="Many (ex: the services there are)" />
          </SlRadio>
        </SlRadioGroup>
        <SlRadioGroup
          className="tags__input tags__choice"
          label={intl.formatMessage({ id: "app.tags.howFilled", defaultMessage: "How is it filled in?" })}
          value={closed ? "list" : "text"}
          onSlChange={(event) => setClosed(event.target.value === "list")}
        >
          <SlRadio value="list">
            <FormattedMessage id="app.tags.list" defaultMessage="Picked from options you define" />
          </SlRadio>
          <SlRadio value="text">
            <FormattedMessage id="app.tags.text" defaultMessage="Written freely on each point" />
          </SlRadio>
        </SlRadioGroup>
      </>}

      <div className="tags__buttons">
        <SlButton disabled={loading} onClick={onCancel}>
          <FormattedMessage id="app.dialog.confirm.cancel" defaultMessage="Cancel" />
        </SlButton>
        <SlButton type="submit" variant="primary" className="dark-btn" loading={loading}>
          <FormattedMessage id="app.dialog.confirm.ok" defaultMessage="Ok" />
        </SlButton>
      </div>
    </form>
  );
};
