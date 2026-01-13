import { lazy, useState, useEffect } from "react";
import { FormattedMessage } from "react-intl";

import SlSwitch from "@shoelace-style/shoelace/dist/react/switch/index.js";

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
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  const [withPhotos, setWithPhotos] = useState(true);
  const [withVideos, setWithVideos] = useState(true);
  const [withAudios, setWithAudios] = useState(true);
  const [withText, setWithText] = useState(false);

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
    options: {
      withPhotos, withVideos, withAudios, withText,
    }
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

  // There's data for the map!
  const dataAvailable = files && data && data.features && data.features.length > 0;

  const handleWithPhotosChange = () => setWithPhotos((val) => !val);
  const handleWithVideosChange = () => setWithVideos((val) => !val);
  const handleWithAudiosChange = () => setWithAudios((val) => !val);
  const handleWithTextChange = () => setWithText((val) => !val);

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
                  onFilesLoad={handleFiles}
                  onDataFileLoad={handleDataFile}
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

      <sl-dialog
        open={settingsDialogOpen}
        onSlAfterHide={() => setSettingsDialogOpen(false)}
      >
        <h2 slot="label" className="dialog__title">
          <FormattedMessage id="app.home.openChatExport" defaultMessage="Open your chat export" />
        </h2>

        <p className="dialog__locations">
          <FormattedMessage
            id="app.home.dialog.locations"
            defaultMessage="{num} location points found"
            values={{ num: data.features.length }}
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
          <SlSwitch size="small" checked={withPhotos && "checked"} onSlChange={handleWithPhotosChange}>
            <span className="dialog__switchtext">
              <FormattedMessage
                id="app.home.dialog.options.photos"
                defaultMessage="Include photos"
              />
            </span>
          </SlSwitch>
        </div>
        <div className="dialog__switchcontainer">
          <SlSwitch size="small" checked={withVideos && "checked"} onSlChange={handleWithVideosChange}>
            <span className="dialog__switchtext">
              <FormattedMessage
                id="app.home.dialog.options.videos"
                defaultMessage="Include videos"
              />
            </span>
          </SlSwitch>
        </div>
        <div className="dialog__switchcontainer">
          <SlSwitch size="small" checked={withAudios && "checked"} onSlChange={handleWithAudiosChange}>
            <span className="dialog__switchtext">
              <FormattedMessage
                id="app.home.dialog.options.audios"
                defaultMessage="Include audios"
              />
            </span>
          </SlSwitch>
        </div>
        <div className="dialog__switchcontainer">
          <SlSwitch size="small" checked={withText && "checked"} onSlChange={handleWithTextChange}>
            <span className="dialog__switchtext">
              <FormattedMessage
                id="app.home.dialog.options.text"
                defaultMessage="Include text messages"
              />
            </span>
          </SlSwitch>
        </div>

        <sl-button variant="primary" className="dialog__btn dark-btn" onClick={() => setSettingsDialogOpen(false)}>
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
