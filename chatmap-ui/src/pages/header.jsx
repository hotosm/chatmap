import { FormattedMessage } from 'react-intl';
import { NavLink } from 'react-router';

import '@hotosm/hanko-auth';
import "@hotosm/tool-menu";

import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';
import SlDropdown from '@shoelace-style/shoelace/dist/react/dropdown/index.js';
import SlIcon from '@shoelace-style/shoelace/dist/react/icon/index.js';
import SlIconButton from '@shoelace-style/shoelace/dist/react/icon-button/index.js';
import SlMenu from '@shoelace-style/shoelace/dist/react/menu/index.js';
import SlMenuItem from '@shoelace-style/shoelace/dist/react/menu-item/index.js';

import DownloadButton from '../components/DownloadButton';
import SaveButton from '../components/SaveButton';
import ShareButton from '../components/ShareButton';
import TagsOptions from "../components/TagsOptions/index.jsx";
import logo from '../assets/hot-logo-gray.svg';
import { locales, localeNames } from '../lang';
import { useAuth } from './../context/AuthContext';
import { useConfigContext } from '../context/ConfigContext.jsx';
import { useLanguage } from '../context/LanguageContext';
import { useMapDataContext } from '../context/MapDataContext.jsx';

export default function Header({
  dataAvailable,
  dataFiles,
  mode,
  showDownloadButton,
  handleNewUploadClick,
  showUploadButton,
  title
}) {
  const { data, tags, mapDataDispatch } = useMapDataContext();
  const { config } = useConfigContext();
  const { lang, setLang } = useLanguage();
  const { isAuthenticated } = useAuth();

  const selectTagHandler = tag => {
    mapDataDispatch({
      type: 'set_filter_tag',
      payload: {tag: tag},
    });
  }

  // Temporary code for show/hide the login button
  const enableExperimental = new URLSearchParams(window.location.search).get('experimental') === 'true';

  function handleLanguageChange(event) {
    const lang = event.detail.item.value;

    setLang(lang);
  }

  return (
    <>
      <header className="header">
        {/* Logo */}
        <div className="header__title">
          <a href={`/${enableExperimental ? "?experimental=true" : ""}`} className="header__logo-link">
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
          {/* <a href="#how"><FormattedMessage id="app.navigation.howDoesItWork" defaultMessage="How does it work?" /></a> */}

          { showUploadButton ?
          <div className="newFile">
              <SlButton
                  variant="default"
                  outline
                  size="small"
                  onClick={handleNewUploadClick}
              >
                  <SlIcon name="arrow-clockwise" slot="prefix"></SlIcon>
                  <FormattedMessage
                      id = "app.uploadNewFile"
                      defaultMessage="New file"
                  />
              </SlButton>
          </div> : null}

          {showDownloadButton && mode !== 'linked' && dataAvailable && <>
            <div className="saveFile">
              <DownloadButton data={data} dataFiles={dataFiles} />
            </div>

            <SaveButton data={data} />
          </>}

          {mode === 'linked' && dataAvailable &&
            <ShareButton sharing={data.sharing} />
          }

          {mode !== 'linked' && Object.keys(tags).length > 0 &&
            <div className="tagsOptions">
              <TagsOptions
                  onSelectTag={selectTagHandler}
                  tags={tags}
                  selectedTag={data.filterTag}
              />
            </div>
          }

          { isAuthenticated && config.ENABLE_LIVE && enableExperimental && mode !== 'linked' && !dataAvailable &&
          <SlButton className="header__live-button" href="#linked" variant="default" outline size="small">
            <FormattedMessage id="app.navigation.live" defaultMessage="Live" />
          </SlButton>
          }

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

          { config.ENABLE_AUTH && enableExperimental &&
          <div className="header__login-button">
            <hotosm-auth
              hanko-url={config.HANKO_API_URL}
              login-url={config.LOGIN_URL}
              redirect-after-login={`${window.location.origin}?experimental=true`}
              redirect-after-logout={`${window.location.origin}?experimental=true`}
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
