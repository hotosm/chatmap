import { FormattedMessage } from "react-intl";

import SlSwitch from "@shoelace-style/shoelace/dist/react/switch/index.js";
import SlDialog from "@shoelace-style/shoelace/dist/react/dialog/index.js";

export default function SettingsDialog({
  open, setOpen, numFeatures, sources,
  withPhotos, setWithPhotos,
  withVideos, setWithVideos,
  withAudios, setWithAudios,
  withText, setWithText,
}) {
  const handleWithPhotosChange = () => setWithPhotos((val) => !val);
  const handleWithVideosChange = () => setWithVideos((val) => !val);
  const handleWithAudiosChange = () => setWithAudios((val) => !val);
  const handleWithTextChange = () => setWithText((val) => !val);

  return (
    <SlDialog
      open={open}
      onSlAfterHide={() => setOpen(false)}
    >
      <h2 slot="label" className="dialog__title">
        <FormattedMessage id="app.home.openChatExport" defaultMessage="Open your chat export" />
      </h2>

      <p className="dialog__locations">
        <FormattedMessage
          id="app.home.dialog.locations"
          defaultMessage="{num} location point(s) found"
          values={{ num: numFeatures }}
        />
      </p>
      <p className="dialog__exporttype">
        <FormattedMessage
          id="app.home.dialog.exporttype"
          defaultMessage="File is a {type} export"
          values={{ type: sources.join(', ') }}
        />
      </p>

      <div className="dialog__switchcontainer">
        <SlSwitch size="small" checked={withPhotos && "checked"} onSlChange={handleWithPhotosChange}>
          <span className="dialog__switchtext">
            <FormattedMessage
              id="app.home.dialog.options.photos"
              defaultMessage="Include photos"
            />
          </span>
        </SlSwitch>
      </div>
      <div className="dialog__switchcontainer">
        <SlSwitch size="small" checked={withVideos && "checked"} onSlChange={handleWithVideosChange}>
          <span className="dialog__switchtext">
            <FormattedMessage
              id="app.home.dialog.options.videos"
              defaultMessage="Include videos"
            />
          </span>
        </SlSwitch>
      </div>
      <div className="dialog__switchcontainer">
        <SlSwitch size="small" checked={withAudios && "checked"} onSlChange={handleWithAudiosChange}>
          <span className="dialog__switchtext">
            <FormattedMessage
              id="app.home.dialog.options.audios"
              defaultMessage="Include audios"
            />
          </span>
        </SlSwitch>
      </div>
      <div className="dialog__switchcontainer">
        <SlSwitch size="small" checked={withText && "checked"} onSlChange={handleWithTextChange}>
          <span className="dialog__switchtext">
            <FormattedMessage
              id="app.home.dialog.options.text"
              defaultMessage="Include text messages"
            />
          </span>
        </SlSwitch>
      </div>

      <sl-button slot="footer" variant="primary" className="dialog__btn dark-btn" onClick={() => setOpen(false)}>
        <FormattedMessage
          id="app.home.dialog.continue"
          defaultMessage="Continue"
        />
      </sl-button>
    </SlDialog>
  );
};
