import { FormattedMessage } from 'react-intl';

export default function Footer() {

  return (
    <>
    <p className="info news">
        <span className="highlighted">
          <strong>News:</strong> Jamaican 🇯🇲 citizens are chat-mapping<br />
          in response for Melissa, check&nbsp;
          <a href="https://umap.hotosm.org/en/map/jamaica-public-response-for-hurricane-melissa_1428">the map</a>
        </span>
    </p>
    <br />
    <p className="info">
      <FormattedMessage
        id = "app.howItWorks"
        defaultMessage="How it works?"
      />
      &nbsp;
      <FormattedMessage
        id = "app.checkThisQuick"
        defaultMessage="Check this quick"
      />
      &nbsp;
      <a href="https://www.youtube.com/watch?v=ScHgVhyj1aw">
        <FormattedMessage
          id = "app.videoTutorial"
          defaultMessage="video tutorial"
        />
      </a>
    </p>
    <p className="info">
          <FormattedMessage
            id = "app.saveYourMapIn"
            defaultMessage="Save your map in"
          />
          &nbsp;
          <a href="https://umap.hotosm.org/chatmap">umap.hotosm.org/chatmap</a>
    </p>
    </>
  );
};