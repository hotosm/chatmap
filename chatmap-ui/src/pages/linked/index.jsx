import { lazy, useState, useEffect, useRef } from 'react';
import useAPI from '../../components/ChatMap/useApi.js'
import Header from '../header.jsx';
import NoLocationsSection from '../home/noLocations.section.jsx';
import { useMapDataContext } from '../../context/MapDataContext.jsx';
import Messages from '../../components/Messages/index.jsx';
import QRCode from '../../components/QRCode/index.jsx';
import { useInterval } from '../../hooks/useInterval.js';

const Map = lazy(() => import('../../components/Map/index.jsx'));

function App() {

  const [noLocations, setNoLocations] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState();
  const [showMessages, setShowMessages] = useState(false);
  const alertRef = useRef();

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
    fetchQRCode,
    fetchStatus
  } = useAPI();

  useInterval(() => { status === "connected" && fetchMapData() }, 10000);

  useInterval(() => fetchStatus(), session && status !== "connected" ? 1000 : null);


  useEffect(() => {
    if (error) {
      alertRef.current.toast()
    }
  }, [error, alertRef]);
 
  useEffect(() => {
    status === "connected" && fetchMapData();
  }, [status]);

  useEffect(() => {
      fetchSession();
  }, []);

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
  }, [mapData]);

  // There's data for the map!
  const dataAvailable = data && data.features && data.features.length > 0;

  const handleFeatureSelect = (feature) => {
    setSelectedFeature(feature.properties);
  }

  return (
    <div className="app">

        <Header
          dataAvailable={dataAvailable}
          mapData={data}
          showChatIcon={false}
          mode="linked"
          subtitle={"Live updated maps with linked devices"}
          legend={"Only WhatsApp is supported for now, more apps coming soon!"}
        />

        <div className={`loading ${
          (isLoading && !QRImgSrc) ? 'loading-show' : 'loading-hide'}`}>
          <sl-badge className="loadingBadge" variant="neutral" pill>Loading ...</sl-badge>
        </div>

        { error ? 
          <sl-alert ref={alertRef} variant="primary" duration="3000" closable>
            <sl-icon slot="icon" name="info-circle"></sl-icon>
            <strong>Something went wrong</strong><br />
            {error}
        </sl-alert> : null }

        { showMessages && dataAvailable &&
          <Messages
            messages={chatMessages}
            selectedFeature={selectedFeature}
          />
        }

        {/* No connected an QR code, show it */}
        { status !== "connected" && QRImgSrc &&
            <QRCode
              img={QRImgSrc}
            />
        }

        {/* There's data, show the map! */}
        { dataAvailable &&
          <Map
            data={data}
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
            <Map center={[1,1]} zoom={1} />
          </div>
        </>
        }

        {/* If there are no locations, show a message */}
        { noLocations &&
          <NoLocationsSection
            handleNewUploadClick={handleNewUploadClick}
          />
        }
    </div>
  );
}

export default App;
