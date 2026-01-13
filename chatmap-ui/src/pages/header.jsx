import { useState, useEffect } from 'react';
import logo from '../assets/hot-logo-gray.svg';
import { FormattedMessage } from 'react-intl';
import { useMapDataContext } from '../context/MapDataContext.jsx';
import SaveButton from '../components/SaveButton';

export default function Header({
  dataAvailable,
  dataFiles,
  handleNewUploadClick,
  showUploadButton,
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
        </div>

        <div className="header__rest">
          <a href=""><FormattedMessage id="app.navigation.howDoesItWork" defaultMessage="How does it work?" /></a>
          <a href=""><FormattedMessage id="app.navigation.blog" defaultMessage="Blog" /></a>
          <sl-icon-button name="translate" />
          {dataAvailable ? <SaveButton data={data} dataFiles={dataFiles} /> : null }
          <sl-button variant="neutral" size="small" className="dark-btn"><FormattedMessage id="app.navigation.login" defaultMessage="Login" /></sl-button>
          <a href=""><sl-icon name="grid-3x3-gap"></sl-icon></a>
        </div>
      </header>
    </>
  );
}
