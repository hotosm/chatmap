import { useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";
import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';
import SlColorPicker from "@shoelace-style/shoelace/dist/react/color-picker/index.js";
// The texts of the color picker in the languages of the app that Shoelace has
import "@shoelace-style/shoelace/dist/translations/de.js";
import "@shoelace-style/shoelace/dist/translations/es.js";
import "@shoelace-style/shoelace/dist/translations/fr.js";
import "@shoelace-style/shoelace/dist/translations/id.js";
import "@shoelace-style/shoelace/dist/translations/it.js";
import "@shoelace-style/shoelace/dist/translations/nl.js";
import "@shoelace-style/shoelace/dist/translations/pt.js";

// Colors to pick from; any other can be chosen with the last one
export const VALUE_COLORS = ["#D9414A", "#4FB3BB", "#E9A23B", "#7A4FB5", "#2E4873", "#9A969B"];

// An option of a key with a list: its text, a description, a color (or none) and how long it lasts
export default function ValueForm({ value, loading, onSave, onArchive, onCancel }) {
  const intl = useIntl();

  const [text, setText] = useState(value.value || "");
  const [description, setDescription] = useState(value.description || "");
  // null: no color, the point keeps its own on the map
  const [color, setColor] = useState(value.color ?? null);
  // Hours it lasts after it was last confirmed; empty when it does not expire
  const [expiresAfter, setExpiresAfter] = useState(value.expires_after ? String(value.expires_after) : "");

  const customColor = color !== null && !VALUE_COLORS.includes(color);

  function handleSubmit(event) {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;
    const hours = parseInt(expiresAfter, 10);
    onSave({
      ...value,
      value: trimmed,
      description: description.trim(),
      color,
      expires_after: hours > 0 ? hours : null,
    });
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="tags__colors">
        <button
          type="button"
          className={`tags__color tags__color--none ${color === null ? "tags__color--selected" : ""}`}
          aria-label={intl.formatMessage({ id: "app.tags.noColor", defaultMessage: "No color" })}
          title={intl.formatMessage({ id: "app.tags.noColor", defaultMessage: "No color" })}
          aria-pressed={color === null}
          onClick={() => setColor(null)}
        />
        { VALUE_COLORS.map((item) =>
          <button
            type="button"
            key={item}
            className={`tags__color ${item === color ? "tags__color--selected" : ""}`}
            style={{ backgroundColor: item }}
            aria-label={item}
            aria-pressed={item === color}
            onClick={() => setColor(item)}
          />
        )}
        {/* Any other color, in a picker of the page: the one of the browser looks
            like the system and speaks its language */}
        <SlColorPicker
          className={`tags__picker ${customColor ? "tags__picker--selected" : ""}`}
          size="small"
          hoist
          noFormatToggle
          lang={intl.locale}
          value={customColor ? color : ""}
          title={intl.formatMessage({ id: "app.tags.otherColor", defaultMessage: "Other color" })}
          label={intl.formatMessage({ id: "app.tags.otherColor", defaultMessage: "Other color" })}
          onSlChange={(event) => event.target.value && setColor(event.target.value.toUpperCase())}
        />
      </div>

      <SlInput
        className="tags__input"
        required
        maxlength={40}
        value={text}
        label={intl.formatMessage({ id: "app.tags.optionLabel", defaultMessage: "Option" })}
        placeholder={intl.formatMessage({ id: "app.tags.optionPlaceholder", defaultMessage: "Ex: Closed" })}
        onSlInput={(event) => setText(event.target.value)}
      />
      <SlInput
        className="tags__input"
        maxlength={200}
        value={description}
        label={intl.formatMessage({ id: "app.tags.descriptionLabel", defaultMessage: "Description" })}
        placeholder={intl.formatMessage({ id: "app.tags.descriptionPlaceholder", defaultMessage: "Ex: Nobody can pass" })}
        onSlInput={(event) => setDescription(event.target.value)}
      />
      <SlInput
        className="tags__input"
        type="number"
        min={1}
        max={720}
        value={expiresAfter}
        label={intl.formatMessage({ id: "app.tags.expiresLabel", defaultMessage: "Expires after (hours)" })}
        placeholder={intl.formatMessage({ id: "app.tags.expiresNever", defaultMessage: "Never" })}
        help-text={intl.formatMessage({
          id: "app.tags.expiresHelp",
          defaultMessage: "If nobody confirms it in that time, the point shows as unknown."
        })}
        onSlInput={(event) => setExpiresAfter(event.target.value)}
      />

      <div className="tags__buttons">
        { value.id &&
          <SlButton variant="text" className="tags__aside" disabled={loading} onClick={() => onArchive(value)}>
            <FormattedMessage id="app.tags.archive" defaultMessage="Archive" />
          </SlButton>
        }
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
