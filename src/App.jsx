import React, { useState, useEffect, useRef } from 'react';
import logo from './hot-logo.svg';
import './App.css';
import FileUpload from './components/FileUpload/index.jsx'
import Map from './components/Map/index.jsx'
import DownloadButton from './components/DownloadButton';
import NavBar from './components/NavBar';
import NavModal from './components/NavModal';
import Settings from "./components/Settings/index.jsx";
import useSettings from './hooks/useSettings';
import useWhatsappParser from './hooks/useWhatsappParser';
import { FormattedMessage } from 'react-intl';

function App() {

  const [content, setContent] = useState(null);
  const [data, setData] = useState(null);
  const [dataFiles, setDataFiles] = useState({});
  const [modalContent, setModalContent] = useState(null);
  const [settings, handleSettingsChange] = useSettings({
    msgPosition: "closest"
  });
  const [geoJson] = useWhatsappParser({ text: content, msgPosition: settings.msgPosition});
  
  const handleFile = (fileContent) => {
    setContent(fileContent)
  }
  const handleDataFile = (filename, fileContent) => {
    setDataFiles(prevData => ({
      ...prevData,
      [filename]: fileContent
    }));
  }

  useEffect(() => {
    if (!geoJson) return;
    setData(geoJson);
  }, [geoJson]);
  
  const handleNewUploadClick = () => {
    setContent(null);
    setData(null);
  }

  const handleModalClose = () => {
    setModalContent(null);
  }

  useEffect(() => {
    setData(null);
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
        <h1 className={data && data.features.length > 0 ? "titleSmall" : ""} >WhatsApp <strong>ChatMap</strong></h1>
        { data && data.features.length > 0 ?
        <div className="fileOtions">
            <DownloadButton data={data} filename="whatsapp-locations" />
            <button onClick={handleNewUploadClick} className="secondaryButton">
              <FormattedMessage
                id = "app.uploadNewFile"
                defaultMessage="Upload new file"
              /> 
            </button>
        </div>
        :
        <>
          <p>
            <FormattedMessage
              id = "app.subtitle"
              defaultMessage="Export a chat from the app and visualize the locations shared in the conversation"
            />
          </p>
          <div className="copy">
            <span>Free and Open Source Software by</span>
            <img src={logo} className="logo" alt="logo" />
          </div>
        </>
      }
      </header>
      { !content &&
        <>
          <div className="fileUpload">
            <FileUpload onDataFileLoad={handleDataFile} onFileLoad={handleFile} />
          </div>
          <p>
            <FormattedMessage
              id = "app.config.msgPositionTextStart"
              defaultMessage="It will search for locations and the"
            />&nbsp;<strong>{ configMsgPositionText }</strong> <FormattedMessage
              id = "app.config.msgPositionTextEnd"
              defaultMessage="message from the same user."
            />
          </p>
          <a className="githubLink" href="https://github.com/hotosm/chatmap">https://github.com/hotosm/chatmap</a>
        </>
      }
      { data && data.features.length > 0 && 
        <div className="data">
          <div className="map">
            <Map data={data} dataFiles={dataFiles}/>
          </div>
        </div>
      }
      { data && data.features.length === 0 && 
        <>
          <h2>No locations found in this file.</h2>
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
