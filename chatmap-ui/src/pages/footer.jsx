import { FormattedMessage } from 'react-intl';

export default function Footer() {

  const ENABLE_LIVE = window._CHATMAP_CONFIG("ENABLE_LIVE", false);

  return (
    <>
    <p className="info">
        <strong>
            <FormattedMessage
              id = "app.howItWorks"
              defaultMessage="How it works?"
            />
          </strong>
          &nbsp;
          <FormattedMessage
            id = "app.checkThisQuick"
            defaultMessage="Check this quick"
          />
          &nbsp;
          <strong><a href="https://www.youtube.com/watch?v=ScHgVhyj1aw">
          <FormattedMessage
            id = "app.videoTutorial"
            defaultMessage="video tutorial"
          />
          </a></strong>
    </p>
    <p className="info">
          <FormattedMessage
            id = "app.saveYourMapIn"
            defaultMessage="Save your map in"
          />
          &nbsp;
          <a href="https://umap.hotosm.org/chatmap">umap.hotosm.org/chatmap</a>
    </p>
    { ENABLE_LIVE ?
    <p className="info info-top-spaced">
        <sl-button size="medium" href="#linked">
          <i className="bi bi-qr-code-scan"></i>
          <sl-icon name="qr-code-scan" slot="prefix"></sl-icon>
          <strong>
            <FormattedMessage
              id = "app.linked.linkYourDevice"
              defaultMessage="Link your device"
            />
          </strong>
          <sl-badge variant="success" pill>
            <FormattedMessage
              id = "app.experimental"
              defaultMessage="Experimental"
            />
          </sl-badge>
        </sl-button>
    </p>
    : null }
    </>
  );
};