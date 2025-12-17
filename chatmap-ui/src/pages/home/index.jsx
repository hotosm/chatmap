import { lazy, useState, useEffect } from "react";
import { FormattedMessage } from "react-intl";

import useFileManager from "../../components/FileUpload/useFileManager.js";
import useContentMerger from "../../components/ChatMap/useContentMerger.js";
import Header from "../header.jsx";
import Footer from "../footer.jsx";
import FileUploadSection from "./fileUpload.section.jsx";
import NoLocationsSection from "./noLocations.section.jsx";
import { useMapDataContext } from "../../context/MapDataContext.jsx";
import "../../styles/home.css";
import logo from "../../assets/chatmap-home.png";

const Map = lazy(() => import("../../components/Map/index.jsx"));

function App() {
  const [noLocations, setNoLocations] = useState(false);
  const [mediaOnly, setMediaOnly] = useState(true);

  // File Manager: Manages files and data files.
  // - handleFiles: handle all chat files
  // - handleDataFile: handle all other files (images, videos)
  // - resetFileManager: clear files and data files states
  // - dataFiles: stores all other files (images, videos)
  // - files: stores all chat files
  const [handleFiles, handleDataFile, resetFileManager, dataFiles, files] = useFileManager();

  // Content Merger: Handle chat content
  // - mapData: ready to use GeoJSON data created from chats
  // - resetMerger: clean everthing to upload a new file
  const [mapData, resetMerger] = useContentMerger({
    files: files,
    options: { mediaOnly }
  });

  // Map Data Context: Manages map data
  const { data, mapDataDispatch } = useMapDataContext();

  // Updates map data context with new map data
  useEffect(() => {
    mapDataDispatch({
      type: 'set',
      payload: mapData,
    });
    // Public event for external integratons
    if (mapData.features.length > 0) {
      window._CHATMAP?.mapData && window._CHATMAP.mapData();
    }
  }, [mapData]);

  // The user wants to upload a new file, clear everything
  // (files, map data, errors)
  const handleNewUploadClick = () => {
    resetFileManager();
    resetMerger();
    setNoLocations(false);
  }

  // Handle uploaded files error (ex: invalid chat export)
  const handleFilesError = () => {
    setNoLocations(true);
  }

  // Handle media only switch
  const handleMediaOnlyChange = () => {
    setMediaOnly(prevState => !prevState);
  }

  // There's data for the map!
  const dataAvailable = files && data && data.features && data.features.length > 0;

  return (
    <>
      <div className="app">
        <Header
          dataAvailable={dataAvailable}
          dataFiles={dataFiles}
          mapData={data}
          handleNewUploadClick={handleNewUploadClick}
          showUploadButton={true}
        />

        <section className="home">
          <div className="home__center">
            <div className="home__actions">
              <h1 className="home__title">ChatMap</h1>
              <p className="home__subtitle"><FormattedMessage id="app.home.subtitle" defaultMessage="Convert your chats into maps."/></p>
              <sl-button size="large" className="featured">
                <sl-icon slot="prefix" name="file-earmark-plus-fill"></sl-icon>
                <FormattedMessage id="app.home.openChatExport" defaultMessage="Open your chat export" />
              </sl-button>
              <p className="home__note">
                <FormattedMessage id="app.home.itWorks" defaultMessage="It works with WhatsApp, Telegram or Signal" />
              </p>
            </div>
            <div className="home__image">
              <img src={logo} />
            </div>
          </div>
        </section>

        <Footer />
      </div>
    </>
  );
}

export default App;
