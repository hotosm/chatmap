import { useState, useEffect } from 'react';
import logo from '../assets/hot-logo-gray.svg';
import { FormattedMessage } from 'react-intl';
import { useMapDataContext } from '../context/MapDataContext.jsx';
import SaveButton from '../components/SaveButton';
import ShareButton from '../components/ShareButton';

export default function Header({
  dataAvailable,
  dataFiles,
  mode,
  showDownloadButton,
  title
}) {
  const { data, tags, mapDataDispatch } = useMapDataContext();

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
          {showDownloadButton && mode !== 'linked' && dataAvailable ? <SaveButton data={data} dataFiles={dataFiles} /> : null }
          {mode === 'linked' && dataAvailable ? <ShareButton sharing={data.sharing} /> : null }
          {mode !== 'linked' && !dataAvailable && <sl-button href="#linked" variant="default" outline size="small"><FormattedMessage id="app.navigation.live" defaultMessage="Live" /></sl-button>}
          {/* <sl-button disabled variant="neutral" size="small" className="dark-btn"><FormattedMessage id="app.navigation.login" defaultMessage="Login" /></sl-button> */}
        </div>
      </header>
    </>
  );
}
