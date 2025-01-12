import React, { useState, useEffect } from 'react';
import logo from './hot-logo.svg';
import './App.css';
import FileUpload from './components/FileUpload/index.jsx'
import Map from './components/Map/index.jsx'
import DownloadButton from './components/DownloadButton';
import NavBar from './components/NavBar';
import NavModal from './components/NavModal';
import Settings from "./components/Settings/index.jsx";
import useSettings from './hooks/useSettings';
import useFileManager from './hooks/useFileManager';
import useContentMerger from './hooks/useContentMerger';
import { FormattedMessage } from 'react-intl';

function App() {

  const [modalContent, setModalContent] = useState(null);
  const [settings, handleSettingsChange] = useSettings({
    msgPosition: "closest"
  });
  const [handleFiles, handleDataFile, resetFileManager, dataFiles, files] = useFileManager();
  const [mapData, resetMerger] = useContentMerger({
    files: files,
    msgPosition: settings.msgPosition
  });
  
  const handleNewUploadClick = () => {
    resetFileManager()
    resetMerger();
  }

  const handleModalClose = () => {
    setModalContent(null);
  }

  useEffect(() => {
    setModalContent(null);
  }, [settings.msgPosition])

  let configMsgPositionText;
  if (settings.msgPosition === "before") {
    configMsgPositionText = <FormattedMessage
      id = "app.config.closestPreviousMsg"
      defaultMessage="previous"
    />
  } else if (settings.msgPosition === "after") {
    configMsgPositionText = <FormattedMessage
      id = "app.config.closestNextMsg"
      defaultMessage="next"
    />
  } else {
    configMsgPositionText = <FormattedMessage
      id = "app.config.closestMsg"
      defaultMessage="closest"
    />
  }

  const dataAvailable = files && mapData && mapData.features.length > 0;
  const noLocations = files && mapData && mapData.features.length === 0;

  return (
    <div className="app">
      <header className="header">
        <div className="top">
          <NavBar onOptionClick={(option) => {
            if (option === "options") {
                setModalContent(<Settings settings={settings} onChange={handleSettingsChange} />)
            }
          }} />
          <NavModal isOpen={modalContent !== null} onClose={handleModalClose} content={modalContent} />
        </div>
        <h1 className={dataAvailable ? "titleSmall" : ""} ><strong>ChatMap</strong></h1>
        { dataAvailable ?
        <div className="fileOtions">
            <DownloadButton data={mapData} filename="chat-locations" />
            <button onClick={handleNewUploadClick} className="secondaryButton">
              <FormattedMessage
                id = "app.uploadNewFile"
                defaultMessage="Upload new file"
              /> 
            </button>
        </div>
        :
        <>
          <p className="subtitle">
            <FormattedMessage
              id = "app.subtitle"
              defaultMessage="Export a chat from the app and visualize the locations shared in the conversation"
            />
          </p>
          <p className="supportedApps">
            <FormattedMessage
              id = "app.supportedApps"
              defaultMessage="Now it works with WhatsApp, Telegram or Signal!"
            />
          </p>
        </>
      }
      </header>
      { !files &&
        <>
          <div className="fileUpload">
            <FileUpload onDataFileLoad={handleDataFile} onFilesLoad={handleFiles} />
          </div>
          <p className="configDesc">
            <FormattedMessage
              id = "app.config.msgPositionTextStart"
              defaultMessage="It will search for locations and the"
            />&nbsp;<strong>{ configMsgPositionText }</strong> <FormattedMessage
              id = "app.config.msgPositionTextEnd"
              defaultMessage="message from the same user."
            />
          </p>
          <div className="infoLinks">
            <div className="copy">
            <a className="github" href="https://github.com/hotosm/chatmap"></a>
              <span>Free and Open Source Software by</span>
              <a href="https://hotosm.org"><img src={logo} className="logo" alt="logo" /></a>
            </div>
            <a href="https://www.hotosm.org/privacy">We collect zero data. https://www.hotosm.org/privacy</a>
          </div>
        </>
      }
      { dataAvailable && 
        <div className="data">
          <div className="map">
            <Map data={mapData} dataFiles={dataFiles}/>
          </div>
        </div>
      }
      { noLocations && 
        <>
          <h2>
            <FormattedMessage
              id = "app.nolocations"
              defaultMessage="No locations found in this file"
            />
          </h2>
          <button onClick={handleNewUploadClick} className="secondaryButton">
          <FormattedMessage
              id = "app.uploadNewFile"
              defaultMessage="Upload new file"
            /> 
          </button>
        </>
      }
    </div>
  );
}

export default App;
