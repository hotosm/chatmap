import { useEffect, useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlDialog from "@shoelace-style/shoelace/dist/react/dialog/index.js";
import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";
import SlTextarea from "@shoelace-style/shoelace/dist/react/textarea/index.js";
import SlButton from "@shoelace-style/shoelace/dist/react/button/index.js";

// The message the bot sends once the user has failed too many times in a
// row, and the two answers offered to cancel or restart. The preview shows
// the two words in bold instead of the numbers WhatsApp adds to them, so the
// owner isn't misled into thinking the user has to type "1" or "2".
export default function MaxAttemptsDialog({ open, setOpen, maxAttempts, onSave }) {
  const intl = useIntl();

  const [quantity, setQuantity] = useState(3);
  const [notifyMessage, setNotifyMessage] = useState("");
  const [toCancel, setToCancel] = useState("");
  const [toRestart, setToRestart] = useState("");

  // Reopening has to start from the map's own configured values
  useEffect(() => {
    if (!open || !maxAttempts) return;
    setQuantity(maxAttempts.max_attempts_quantity);
    setNotifyMessage(maxAttempts.notify_message || "");
    setToCancel(maxAttempts.to_cancel || "");
    setToRestart(maxAttempts.to_restart || "");
  }, [open, maxAttempts]);

  if (!maxAttempts) return null;

  function handleSave() {
    onSave({
      max_attempts_quantity: Number(quantity) || 1,
      notify_message: notifyMessage,
      to_cancel: toCancel,
      to_restart: toRestart,
    });
    setOpen(false);
  }

  return (
    <SlDialog open={open} onSlAfterHide={() => setOpen(false)}>
      <h2 slot="label" className="dialog__title">
        <FormattedMessage id="app.botSetup.maxAttemptsTitle" defaultMessage="Cancel or restart" />
      </h2>

      <div className="botSetup__dialog-fields">
        <SlInput
          type="number"
          min="1"
          label={intl.formatMessage({
            id: "app.botSetup.maxAttemptsQuantity",
            defaultMessage: "Failed attempts before offering to cancel or restart",
          })}
          value={quantity}
          onSlInput={(event) => setQuantity(event.target.value)}
        />

        <SlTextarea
          rows="3"
          resize="auto"
          label={intl.formatMessage({
            id: "app.botSetup.notifyMessage",
            defaultMessage: "Warning message",
          })}
          placeholder={intl.formatMessage({
            id: "app.botSetup.notifyMessagePlaceholder",
            defaultMessage: "What the bot sends when the user reaches that limit",
          })}
          value={notifyMessage}
          onSlInput={(event) => setNotifyMessage(event.target.value)}
        />

        <SlInput
          label={intl.formatMessage({ id: "app.botSetup.toCancel", defaultMessage: "Option to cancel" })}
          value={toCancel}
          onSlInput={(event) => setToCancel(event.target.value)}
        />

        <SlInput
          label={intl.formatMessage({ id: "app.botSetup.toRestart", defaultMessage: "Option to restart" })}
          value={toRestart}
          onSlInput={(event) => setToRestart(event.target.value)}
        />
      </div>

      <div className="botSetup__preview">
        <span className="botSetup__preview-label">
          <FormattedMessage id="app.botSetup.preview" defaultMessage="What the user will see" />
        </span>
        <p className="botSetup__preview-text">{notifyMessage}</p>
        <p className="botSetup__preview-text">
          <strong>{toCancel}</strong> / <strong>{toRestart}</strong>
        </p>
      </div>

      <div slot="footer" className="botSetup__dialog-buttons">
        <SlButton variant="default" outline onClick={() => setOpen(false)}>
          <FormattedMessage id="app.botSetup.cancel" defaultMessage="Cancel" />
        </SlButton>
        <SlButton variant="primary" onClick={handleSave}>
          <FormattedMessage id="app.botSetup.save" defaultMessage="Save changes" />
        </SlButton>
      </div>
    </SlDialog>
  );
}
