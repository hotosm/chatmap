import { FormattedMessage } from 'react-intl';

export default function Footer() {

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
    </>
  );
};