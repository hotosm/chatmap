import { lazy, useState, useEffect } from 'react';
import useAPI from '../../components/ChatMap/useApi.js'
import Header from '../header.jsx';
import { useMapDataContext } from '../../context/MapDataContext.jsx';
import QRCode from '../../components/QRCode';
import { useInterval } from '../../hooks/useInterval.js';
import Settings from '../../components/Settings';
import { useNavigate } from "react-router-dom";
import { useIntl } from 'react-intl';

const Map = lazy(() => import('../../components/Map'));

function App() {

  const intl = useIntl();

  const [, setSelectedFeature] = useState();
  const [showSettings, setShowSettings] = useState(false);
  const navigate = useNavigate();

  // Get data from API
  const {
    mapData,
    QRImgSrc,
    session,
    status,
    isLoading,
    error,
    fetchMapData,
    fetchSession,
    logoutSession,
    fetchQRCode,
    fetchStatus
  } = useAPI();

  // If connected, fetch map data every 10 sec
  useInterval(() => { status === "connected" && fetchMapData() }, 10000);
  // If connected, fetch map data
  useEffect(() => {
    status === "connected" && fetchMapData();
  }, [status]);

  // If not connected, fetch status every 1 sec
  useInterval(() => fetchStatus(), session && status !== "connected" ? 1000 : null);

  // Fetch user session
  useEffect(() => {
      fetchSession();
  }, []);

  // If session not found or waiting for connection
  // but no QR code available, fetch a QR code
  useEffect(() => {
    if (
      (status === "not_found" && session) ||
      (status === "waiting" && !QRImgSrc)
     ) {
      fetchQRCode(session);
    }
  }, [session, status, QRImgSrc]);

  // Map Data Context: Manages map data
  const { data, mapDataDispatch } = useMapDataContext();

  // Updates map data context with new map data
  useEffect(() => {
    mapDataDispatch({
      type: 'set',
      payload: mapData,
    });
    if (mapData.id) {
      history.replaceState(null, '', `/#map/${mapData.id}`);
    }
  }, [mapData]);

  // There's data for the map!
  const dataAvailable = data && data.features && data.features.length > 0;

  const handleFeatureSelect = (feature) => {
    setSelectedFeature(feature.properties);
  }

  const handleSettingsClick = () => {
    setShowSettings(!showSettings);
  }

  const handleSettingsCloseClick = () => {
    setShowSettings(false);
  }

  const handleLogoutClick = async () => {
    await logoutSession();
    navigate("/", { replace: true });
  }

  return (
    <div className="app">

        <Header
          dataAvailable={dataAvailable}
          handleSettingsClick={handleSettingsClick}
          mapData={data}
          showLogoutIcon={true}
          handleLogoutClick={handleLogoutClick}
          mode="linked"
          subtitle={
            intl.formatMessage({
              id: "app.linked.subtitle",
              defaultMessage: "Live updated maps with linked devices"
            })
          }
          legend={
            intl.formatMessage({
              id: "app.linked.legend",
              defaultMessage: "Only WhatsApp is supported for now, more apps coming soon!"
            })
          }
        />

        {/* Loading message */}
        <div className={`loading ${
          (isLoading && !QRImgSrc) ? 'loading-show' : 'loading-hide'}`}>
          <sl-badge className="loadingBadge" variant="neutral" pill>Loading ...</sl-badge>
        </div>

        {/* Error alerts */}
        <sl-alert open={error ? true : false} variant="primary" duration="3000" closable>
            <sl-icon slot="icon" name="info-circle"></sl-icon>
            <strong>Something went wrong</strong><br />
            {error}
        </sl-alert>

        {/* No connected an QR code, show it */}
        { status !== "connected" && QRImgSrc &&
            <QRCode
              img={QRImgSrc}
            />
        }

        {/* There's data, show the map! */}
        { dataAvailable &&
          <Map
            className="mapFull"
            onSelectFeature={handleFeatureSelect}
          />
        }

        {/* No data, show an empty map */}
        { !dataAvailable &&
        <>
          {status === "connected" &&
            <div className="mapMessage">
              <h2>Your device was linked successfully</h2>
              <h3>Now you can receive <strong>shared locations</strong> plus <br /> <strong>chat messages</strong> and start mapping!</h3>
              <div className="mapSteps">
                  <sl-icon size="large" name="chat-heart"></sl-icon>
                  <span>+</span>
                  <sl-icon size="large" name="chat-square-text"></sl-icon>
                  <span>=</span>
                  <sl-icon size="large" name="pin-map"></sl-icon>
              </div>
            </div>
          }
          <div className="mapDisabled">
            <Map className="mapFull" center={[1,1]} zoom={1} />
          </div>
        </>
        }

        {/* Settings window */}
        { showSettings &&
          <Settings
            handleCloseClick={handleSettingsCloseClick}
          />
        }
    </div>
  );
}

export default App;
