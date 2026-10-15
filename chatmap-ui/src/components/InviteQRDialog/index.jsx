import { useRef, useState } from "react";
import { FormattedMessage } from "react-intl";

import SlButton from "@shoelace-style/shoelace/dist/react/button/index.js";
import SlDialog from "@shoelace-style/shoelace/dist/react/dialog/index.js";
import SlQrCode from "@shoelace-style/shoelace/dist/react/qr-code/index.js";

import { useConfigContext } from "../../context/ConfigContext.jsx";

// TODO: generate a service centralize the API routes
function invitationsUrl(apiUrl, mapId) {
  return `${apiUrl.replace(/\/v\d+$/, "/v2")}/maps/${mapId}/invitations`;
}

export default function InviteQRDialog({ open, setOpen, map }) {
  const { config } = useConfigContext();
  const abortRef = useRef(null);
  const [invitation, setInvitation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  const handleHide = () => {
    abortRef.current?.abort();
    setOpen(false);
    setInvitation(null);
    setLoading(false);
    setFailed(false);
  };

  const handleGenerate = async () => {
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setFailed(false);

    try {
      const response = await fetch(invitationsUrl(config.API_URL, map.id), {
        method: "POST",
        credentials: "include",
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Failed to generate the invitation (${response.status})`);
      }

      setInvitation(await response.json());
    } catch (error) {
      if (error.name !== "AbortError") {
        setFailed(true);
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  };

  return (
    <SlDialog open={open} onSlAfterHide={handleHide}>
      <h2 slot="label" className="dialog__title">
        <FormattedMessage id="app.maps.invite.title" defaultMessage="Invite to map" />
        {map && `: ${map.name}`}
      </h2>

      {invitation ? (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}>
          <SlQrCode value={invitation.url} size={256} label={map?.name} />
          <p>
            <FormattedMessage
              id="app.maps.invite.once"
              defaultMessage="This QR is shown only once. Use it before closing this window."
            />
          </p>
        </div>
      ) : (
        <>
          <p>
            <FormattedMessage
              id="app.maps.invite.description"
              defaultMessage="Generate a QR code so people using the ChatMap app can join this map and add points."
            />
          </p>
          <p>
            <FormattedMessage
              id="app.maps.invite.warning"
              defaultMessage="Generating a new QR invalidates the previous one. People who already joined keep their access."
            />
          </p>
          {failed && (
            <p>
              <FormattedMessage
                id="app.maps.invite.error"
                defaultMessage="The QR could not be generated. Try again."
              />
            </p>
          )}
          <SlButton variant="primary" loading={loading} onClick={handleGenerate}>
            <FormattedMessage id="app.maps.invite.generate" defaultMessage="Generate QR" />
          </SlButton>
        </>
      )}
    </SlDialog>
  );
};
