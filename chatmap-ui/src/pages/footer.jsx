import { FormattedMessage, useIntl } from 'react-intl';
import logo from '../assets/hot-logo-text.svg';

export default function Footer() {
  const ENABLE_LIVE = window._CHATMAP_CONFIG("ENABLE_LIVE", false);
  const intl = useIntl();

  const msg = intl.formatMessage({
    id: "app.footer.become",
    defaultMessage: "become a ChatMapper today!",
  }, {
    chatmapper: "<i>ChatMapper</i>",
  });

  return (
    <footer className="footer">
      <div className="footer__top">
        <div className="footer__top-left">
          <h2 dangerouslySetInnerHTML={{__html: msg}}></h2>

          <ul>
            <li><a href="#"><FormattedMessage id="app.footer.takeTheCourse" defaultMessage="Take the course" /></a></li>
            <li><a href="#"><FormattedMessage id="app.footer.getInspired" defaultMessage="Get inspired" /></a></li>
            <li><a href="#"><FormattedMessage id="app.footer.checkTheDocs" defaultMessage="Check the docs" /></a></li>
          </ul>
        </div>
        <div className="footer__top-right">
          <h3><FormattedMessage id="app.footer.supportTheComunity" defaultMessage="Support the community" /></h3>
          <a href="#"><span><FormattedMessage id="app.footer.getInTouch" defaultMessage="Get in touch" /></span></a>
        </div>
      </div>
      <div className="footer__bottom">
        <div className="footer__logo">
          <img src={logo} alt="hot logo" />
        </div>
        <div className="footer__copy">
          <FormattedMessage id="app.footer.copy" />
        </div>
      </div>
    </footer>
  );
};
