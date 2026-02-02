import { useState, useEffect } from 'react';
import logo from '../assets/hot-logo-gray.svg';
import { FormattedMessage } from 'react-intl';
import { useMapDataContext } from '../context/MapDataContext.jsx';
import { useAuth } from './../context/AuthContext';
import SaveButton from '../components/SaveButton';
import { useConfigContext } from '../context/ConfigContext.jsx';
import ShareButton from '../components/ShareButton';
import getLocalCode from '../lang';
import '@hotosm/hanko-auth';
import "@hotosm/tool-menu";

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
  const [_, langCode] = getLocalCode();
  const { isAuthenticated } = useAuth();

  const selectTagHandler = tag => {
    mapDataDispatch({
      type: 'set_filter_tag',
      payload: {tag: tag},
    });
  }

  const [selected, setSelected] = useState(false);

  useEffect(() => {
    setSelected(false);
  }, [data])

  return (
    <>
      <header className="header">
        {/* Logo */}
        <div className="header__title">
          <a href="/" className="header__logo-link">
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
            <SaveButton data={data} dataFiles={dataFiles} />
          }

          {mode === 'linked' && dataAvailable &&
            <ShareButton sharing={data.sharing} />
          }

          { isAuthenticated && config.ENABLE_LIVE && mode !== 'linked' && !dataAvailable &&
          <sl-button className="header__live-button" href="#linked" variant="default" outline size="small">
            <FormattedMessage id="app.navigation.live" defaultMessage="Live" />
          </sl-button>
          }

          { config.ENABLE_AUTH &&
          <div className="header__login-button">
            <hotosm-auth
              hanko-url={config.HANKO_API_URL}
              login-url={config.LOGIN_URL}
              redirect-after-login={window.location.origin}
              redirect-after-logout={window.location.origin}
              lang={langCode}
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
