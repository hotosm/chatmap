import { lazy, useState, useEffect } from 'react';
import useAPI from '../../components/ChatMap/useApi.js'
import Header from '../header.jsx';
import NoLocationsSection from '../home/noLocations.section.jsx';
import { useMapDataContext } from '../../context/MapDataContext.jsx';
import Messages from '../../components/Messages/index.jsx';
import { useInterval } from '../../hooks/useInterval.js';
import { FormattedMessage } from 'react-intl';

const Map = lazy(() => import('../../components/Map/index.jsx'));

function App() {

  const [noLocations, setNoLocations] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState();
  const [showMessages, setShowMessages] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState('');

  // Get data from API
  const {mapData, QRImgSrc, session, status, files, isLoading, error, fetchMapData, fetchSession, fetchQRCode, fetchStatus} = useAPI();

  useInterval(() => { status === "connected" && fetchMapData() }, status === "connected" && 10000);

  useEffect(() => {
    fetchSession();
  }, []);

  useEffect(() => {
    if (session) {
      fetchQRCode();
    }
  }, [session]);

  useInterval(() => fetchStatus(), session != null && status !== "connected" ? 1000 : null);

  // Map Data Context: Manages map data
  const { data, mapDataDispatch } = useMapDataContext();

  // Updates map data context with new map data
  useEffect(() => {
    mapDataDispatch({
      type: 'set',
      payload: mapData,
    });
  }, [mapData]);

  // The user wants to upload a new file, clear everything
  // (files, map data, errors)
  const handleNewUploadClick = () => {
    resetFileManager();
    resetMerger();
    setNoLocations(false);
    setSelectedFeature()
  }

  // Click header navigation option (ex: show/hide chat)
  const handleOptionClick = option => {
    if (option === "chat") {
      setShowMessages(prev => !prev);
    }
  }

  const handleConnectClick = () => {
    fetchSession(phoneNumber);
    fetchQRCode(phoneNumber);
  }

  // There's data for the map!
  // const dataAvailable = files && data && data.features && data.features.length > 0;
  const dataAvailable = data && data.features && data.features.length > 0;

  const handleFeatureSelect = (feature) => {
    setSelectedFeature(feature.properties);
  }

  return (
    <div className="app">

        <Header
          dataAvailable={dataAvailable}
          mapData={data}
          handleNewUploadClick={handleNewUploadClick}
          handleOptionClick={handleOptionClick}
          mode="linked"
        />

        { showMessages && dataAvailable &&
          <Messages
            messages={chatMessages}
            selectedFeature={selectedFeature}
          />
        }

        { !showMessages && !dataAvailable && !QRImgSrc &&
          <div class="connectForm">
            <input
              type="text"
              placeholder="Phone number"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              className="phoneNumberInput"
            />
            <sl-button
              variant="primary"
              onClick={handleConnectClick}
            >
              <FormattedMessage
                id = "app.connect"
                defaultMessage="Connect"
              />
            </sl-button>
          </div>
        }

        {/* If there're no files, show file upload options */}
        { status === "waiting" && QRImgSrc &&
          <div class="connectForm qrCodeContainer">
            <h3>Scan this QR code with your device:</h3>
            <img class="qrCode" src={QRImgSrc} alt="QR Code" />
          </div>
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
          <Map center={[1,1]} zoom={1} />
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
