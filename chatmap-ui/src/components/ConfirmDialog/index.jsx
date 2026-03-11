import { useCallback } from "react";

import { FormattedMessage } from "react-intl";

import SlDialog from "@shoelace-style/shoelace/dist/react/dialog/index.js";
import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';

export default function ConfirmDialog({
  open, setOpen, onConfirm, data, title, children,
}) {
  const handleClick = useCallback(() => {
    onConfirm(data)
    setOpen(false);
  }, [data]);

  return (
    <SlDialog
      open={open}
      onSlAfterHide={() => setOpen(false)}
    >
      <h2 slot="label" className="dialog__title">
        <FormattedMessage {...title} />
      </h2>

      { children }

      <div slot="footer" style={{display: "flex", gap: "1rem", justifyContent: "flex-end"}}>
        <SlButton variant="default" onClick={() => setOpen(false)}>
          <FormattedMessage id="app.dialog.confirm.cancel" defaultMessage="Cancel" />
        </SlButton>
        <SlButton variant="primary" onClick={handleClick}>
          <FormattedMessage id="app.dialog.confirm.ok" defaultMessage="Ok" />
        </SlButton>
      </div>
    </SlDialog>
  );
};
