import { lazy, useState, useEffect } from "react";
import { FormattedMessage } from "react-intl";

import useFileManager from "../../components/FileUpload/useFileManager.js";
import useContentMerger from "../../components/ChatMap/useContentMerger.js";
import Header from "../header.jsx";
import Footer from "../footer.jsx";
import FileUpload from "../../components/FileUpload/index.jsx";
import { useMapDataContext } from "../../context/MapDataContext.jsx";
import "../../styles/home.css";
import logo from "../../assets/chatmap-home.png";

const Map = lazy(() => import("../../components/Map/index.jsx"));

function App() {
  const [noLocations, setNoLocations] = useState(false);
  const [mediaOnly, setMediaOnly] = useState(true);
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);

  // File Manager: Manages files and data files.
  // - setFiles: handle all chat files
  // - handleDataFile: handle all other files (images, videos)
  // - resetFileManager: clear files and data files states
  // - dataFiles: stores all other files (images, videos)
  // - files: stores all chat files
  const [setFiles, handleDataFile, resetFileManager, dataFiles, files] = useFileManager();

  function handleFiles(files) {
    setFiles(files);
    setSettingsDialogOpen(true);
  }

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

        {!dataAvailable &&
          <section className="home">
            <div className="home__center">
              <div className="home__actions">
                <h1 className="home__title">ChatMap</h1>
                <p className="home__subtitle"><FormattedMessage id="app.home.subtitle" defaultMessage="Convert your chats into maps."/></p>
                <FileUpload
                  mediaOnly={mediaOnly}
                  onFilesLoad={handleFiles}
                  onDataFileLoad={handleDataFile}
                  handleMediaOnlyChange={handleMediaOnlyChange}
                  onError={handleFilesError}
                />
                <p className="home__note">
                  <FormattedMessage id="app.home.itWorks" defaultMessage="It works with WhatsApp, Telegram or Signal" />
                  <sl-icon-button name="plus-circle-dotted" />
                </p>
              </div>
              <div className="home__image">
                <img src={logo} />
              </div>
            </div>
          </section>
        }

        {dataAvailable &&
          <Map
            dataFiles={dataFiles}
          />
        }

        <Footer />
      </div>

      <sl-dialog open={settingsDialogOpen} onSLAfterHide={() => setSettingsDialogOpen(false)}>
        <h2 slot="label" className="dialog__title">
          <FormattedMessage id="app.home.openChatExport" defaultMessage="Open your chat export" />
        </h2>

        <p className="dialog__locations">
          <FormattedMessage
            id="app.home.dialog.locations"
            defaultMessage="{num} location points found"
            values={{ num: 54 }}
          />
        </p>
        <p className="dialog__exporttype">
          <FormattedMessage
            id="app.home.dialog.exporttype"
            defaultMessage="File is a {type} export"
            values={{ type: "WhatsApp" }}
          />
        </p>

        <div className="dialog__switchcontainer">
          <sl-switch size="small" checked>
            <span className="dialog__switchtext">
              <FormattedMessage
                id="app.home.dialog.options.photos"
                defaultMessage="Include photos"
              />
            </span>
          </sl-switch>
        </div>
        <div className="dialog__switchcontainer">
          <sl-switch size="small" checked>
            <span className="dialog__switchtext">
              <FormattedMessage
                id="app.home.dialog.options.videos"
                defaultMessage="Include videos"
              />
            </span>
          </sl-switch>
        </div>
        <div className="dialog__switchcontainer">
          <sl-switch size="small" checked>
            <span className="dialog__switchtext">
              <FormattedMessage
                id="app.home.dialog.options.audios"
                defaultMessage="Include audios"
              />
            </span>
          </sl-switch>
        </div>
        <div className="dialog__switchcontainer">
          <sl-switch size="small">
            <span className="dialog__switchtext">
              <FormattedMessage
                id="app.home.dialog.options.text"
                defaultMessage="Include text messages"
              />
            </span>
          </sl-switch>
        </div>

        <sl-button variant="primary" className="dialog__btn dark-btn">
          <FormattedMessage
            id="app.home.dialog.continue"
            defaultMessage="Continue"
          />
        </sl-button>
      </sl-dialog>
    </>
  );
}

export default App;
