import { FormattedMessage } from 'react-intl';
import { NavLink } from 'react-router';

import '@hotosm/hanko-auth';
import "@hotosm/tool-menu";

import SlDropdown from '@shoelace-style/shoelace/dist/react/dropdown/index.js';
import SlIconButton from '@shoelace-style/shoelace/dist/react/icon-button/index.js';
import SlMenu from '@shoelace-style/shoelace/dist/react/menu/index.js';
import SlMenuItem from '@shoelace-style/shoelace/dist/react/menu-item/index.js';

import logo from '../assets/hot-logo-gray.svg';
import { locales, localeNames } from '../lang';
import { useAuth } from './../context/AuthContext';
import { useConfigContext } from '../context/ConfigContext.jsx';
import { useLanguage } from '../context/LanguageContext';

export default function Header({
  title,
  children,
}) {
  const { config } = useConfigContext();
  const { lang, setLang } = useLanguage();
  const { isAuthenticated } = useAuth();

  function handleLanguageChange(event) {
    const lang = event.detail.item.value;

    setLang(lang);
  }

  return (
    <>
      <header className="header">
        {/* Logo */}
        <div className="header__title">
          <a href={`/`} className="header__logo-link">
            <img src={logo} className="header__logo" alt="hot logo" />
          </a>
          <h1 className="header__title-text">{title}</h1>
          { isAuthenticated && <ul className="header__nav">
            <li>
              <NavLink
                to="/maps"
                style={({ isActive }) => ({ fontWeight: isActive ? "bold" : "" })}
              ><FormattedMessage id="app.navigation.maps" defaultMessage="Maps" /></NavLink>
            </li>
          </ul>}
        </div>

        <div className="header__rest">
          { children }

          <SlDropdown>
            <SlIconButton slot="trigger" name="translate" caret size="small"></SlIconButton>
            <SlMenu onSlSelect={handleLanguageChange}>
              { Object.keys(locales).map((langCode) => (
                <SlMenuItem
                  key={langCode}
                  type="checkbox"
                  value={langCode}
                  checked={ lang === langCode ? "checked" : false }
                >
                  { localeNames[langCode] }
                </SlMenuItem>
              )) }
            </SlMenu>
          </SlDropdown>

          { config.ENABLE_AUTH &&
          <div className="header__login-button">
            <hotosm-auth
              hanko-url={config.HANKO_API_URL}
              login-url={config.LOGIN_URL}
              redirect-after-login={`${window.location.origin}`}
              redirect-after-logout={`${window.location.origin}`}
              lang={lang}
            />
          </div>
          }

          <hotosm-tool-menu
            show-logos={false}
          />
        </div>
      </header>
    </>
  );
}
