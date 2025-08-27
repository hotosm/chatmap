

export default function Footer() {

  const ENABLE_LIVE = window._CHATMAP_CONFIG("ENABLE_LIVE", false);

  return (
    <>
    <p className="info">
        <strong>How it works?</strong> check this quick <strong><a href="https://www.youtube.com/watch?v=ScHgVhyj1aw">video tutorial</a></strong>
    </p>
    <p className="info">
       Save your map in <a href="https://umap.hotosm.org/chatmap">umap.hotosm.org/chatmap</a>
    </p>
    { ENABLE_LIVE ?
        <p className="info info-top-spaced">
            <sl-button size="medium" href="#linked">
              <i className="bi bi-qr-code-scan"></i>
              <sl-icon name="qr-code-scan" slot="prefix"></sl-icon> <strong>Link your device</strong>
              <sl-badge variant="success" pill>New!</sl-badge>
            </sl-button>
        </p>
    : null }
    </>
  );
};