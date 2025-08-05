const ENABLE_LIVE = import.meta.env.VITE_ENABLE_LIVE || false;

export default function Footer() {

  return (
    <>
    <p className="info">
        <strong>From chat to map</strong> check this quick <strong><a href="https://www.youtube.com/watch?v=ScHgVhyj1aw">video tutorial</a></strong>
    </p>
    <p className="info">
       Save your downloaded map in <a href="https://umap.hotosm.org/chatmap">umap.hotosm.org/chatmap</a>
    </p>
    { ENABLE_LIVE ?
    <p className="info info-bottom-spaced">
        Or <a href="#linked">link a device</a> <small>(new!)</small>
    </p>
    : null}
    <div className="infoLinks">
        <div className="copy">
            <a href="https://github.com/hotosm/chatmap">This is free software</a>
        </div>
        <a href="https://www.hotosm.org/privacy">- We collect zero personal data. hotosm.org/privacy -</a>
        &nbsp;
        <a href="https://github.com/hotosm/chatmap">v0.4.11</a>
    </div>
    </>
  );
};