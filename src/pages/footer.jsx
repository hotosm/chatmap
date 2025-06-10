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
            <a href="https://github.com/hotosm/chatmap">Free Software</a>
        </div>
        <a href="https://www.hotosm.org/privacy">- We collect zero personal data. hotosm.org/privacy -</a>
        &nbsp;
        <a href="https://github.com/hotosm/chatmap">v0.4.8</a>
    </div>
    </>
  );
};