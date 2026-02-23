import { FormattedMessage } from 'react-intl';

import '@hotosm/hanko-auth';
import "@hotosm/tool-menu";

import SlOption from '@shoelace-style/shoelace/dist/react/option/index.js';
import SlSelect from '@shoelace-style/shoelace/dist/react/select/index.js';

import logo from '../assets/hot-logo-gray.svg';
import { useMapDataContext } from '../context/MapDataContext.jsx';
import { useAuth } from './../context/AuthContext';
import SaveButton from '../components/SaveButton';
import { useConfigContext } from '../context/ConfigContext.jsx';
import ShareButton from '../components/ShareButton';
import TagsOptions from "../components/TagsOptions/index.jsx";
import { locales, localeNames } from '../lang';
import { useLanguage } from '../context/LanguageContext';

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
    setLang(event.target.value);
  };

  return (
    <>
      <header className="header">
        {/* Logo */}
        <div className="header__title">
          <a href={`/${enableExperimental ? "?experimental=true" : ""}`} className="header__logo-link">
            <img src={logo} className="header__logo" alt="hot logo" />
          </a>
          <h1 className="header__title-text">{title}</h1>
        </div>

        <div className="header__rest">
          {/* <a href="#how"><FormattedMessage id="app.navigation.howDoesItWork" defaultMessage="How does it work?" /></a> */}
          {/* <sl-icon-button name="translate" /> */}

          { showUploadButton ?
          <div className="newFile">
              <sl-button
                  variant="default"
                  outline
                  size="small"
                  onClick={handleNewUploadClick}
              >
                  <sl-icon name="arrow-clockwise" slot="prefix"></sl-icon>
                  <FormattedMessage
                      id = "app.uploadNewFile"
                      defaultMessage="New file"
                  /> 
              </sl-button>
          </div> : null}


          {showDownloadButton && mode !== 'linked' && dataAvailable && 
            <div className="saveFile">
              <SaveButton data={data} dataFiles={dataFiles} />
            </div>
          }

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
          <sl-button className="header__live-button" href="#linked" variant="default" outline size="small">
            <FormattedMessage id="app.navigation.live" defaultMessage="Live" />
          </sl-button>
          }

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

          <SlSelect value={lang} size="small" onSlChange={handleLanguageChange}>
            { Object.keys(locales).map((langCode) => (
              <SlOption value={langCode} key={langCode}>{ localeNames[langCode] }</SlOption>
            )) }
          </SlSelect>

          <hotosm-tool-menu
            show-logos={false}
          />

        </div>
      </header>
    </>
  );
}
