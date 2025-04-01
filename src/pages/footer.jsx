import React from 'react';

export default function Footer() {

  return (
    <>
    <p className="info">
        <strong>From chat to map</strong> check this quick <strong>
        <a href="https://www.youtube.com/watch?v=ScHgVhyj1aw">video tutorial</a></strong>
    </p>
    <div className="infoLinks">
        <div className="copy">
            <a className="github" href="https://github.com/hotosm/chatmap"></a>
            <span>Free and Open Source Software</span>
        </div>
        <a href="https://www.hotosm.org/privacy">We collect zero data. https://www.hotosm.org/privacy</a>
    </div>
    </>
  );
};