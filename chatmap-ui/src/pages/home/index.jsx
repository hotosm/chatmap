import { lazy, useState, useEffect } from "react";
import useFileManager from "../../components/FileUpload/useFileManager.js";
import useContentMerger from "../../components/ChatMap/useContentMerger.js";
import Header from "../header.jsx";
import Footer from "../footer.jsx";
import FileUploadSection from './fileUpload.section.jsx';
import SettingsDialog from "../../components/SettingsDialog/index.jsx";
import { useMapDataContext } from "../../context/MapDataContext.jsx";
import "../../styles/home.css";
import logo from "../../assets/chatmap-home.png";

const Map = lazy(() => import("../../components/Map/index.jsx"));

function App() {
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  const [withPhotos, setWithPhotos] = useState(true);
  const [withVideos, setWithVideos] = useState(true);
  const [withAudios, setWithAudios] = useState(true);
  const [withText, setWithText] = useState(false);

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
    files, withPhotos, withVideos, withAudios, withText,
  });

  // Map Data Context: Manages map data
  const { data, mapDataDispatch } = useMapDataContext();

  useEffect(() => {
      // Public event for external integratons
      if (mapData.features.length > 0) {
        window._CHATMAP?.mapData && window._CHATMAP.mapData();
        setSettingsDialogOpen(true);
      }
  }, [mapData])

  // Updates map data context with new map data
  useEffect(() => {
    mapDataDispatch({
      type: 'set',
      payload: mapData,
    });
  }, [mapData]);

  const confirmPageLeave = (e) => {
    e.preventDefault();
    if (window.confirm("Are you sure?")) {
      return true;
    }
  };

  useEffect(() => {
    if (data.hasChanged === true) {
      window.addEventListener('beforeunload', confirmPageLeave);
    } else {
      window.removeEventListener('beforeunload', confirmPageLeave);
    }
  }, [data.hasChanged]);

  // The user wants to upload a new file, clear everything
  // (files, map data, errors)
  const handleNewUploadClick = () => {
    if (data.hasChanged === true) {
      if (!window.confirm("Are you sure?")) {
        return;
      }
    }
    resetFileManager();
    resetMerger();
    mapDataDispatch({
      type: 'reset'
    })
    window.removeEventListener('beforeunload', confirmPageLeave);
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
          showUploadButton={dataAvailable}
          showDownloadButton={true}
        />

        {!files &&
        <section className="home">
          <div className="home__center">
            <div className="home__actions">
              <h1 className="home__title">ChatMap</h1>
              <FileUploadSection
                handleFiles={handleFiles}
                handleDataFile={handleDataFile}
              />
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
            data={data}
          />
        }

        <Footer
          visible={!dataAvailable}
          className={dataAvailable ? "footer__floating" : ""}
        />
      </div>

      <SettingsDialog
        open={settingsDialogOpen}
        setOpen={setSettingsDialogOpen}
        numFeatures={data.features.length}
        sources={data._sources}
        withPhotos={withPhotos} setWithPhotos={setWithPhotos}
        withVideos={withVideos} setWithVideos={setWithVideos}
        withAudios={withAudios} setWithAudios={setWithAudios}
        withText={withText} setWithText={setWithText}
      ></SettingsDialog>
    </>
  );
}

export default App;
