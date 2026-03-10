import { lazy, useState, useEffect } from "react";
import { FormattedMessage } from "react-intl";

import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';
import SlIcon from '@shoelace-style/shoelace/dist/react/icon/index.js';

import useFileManager from "../../components/FileUpload/useFileManager.js";
import useContentMerger from "../../components/ChatMap/useContentMerger.js";
import Header from "../header.jsx";
import Footer from "../footer.jsx";
import FileUploadSection from './fileUpload.section.jsx';
import SettingsDialog from "../../components/SettingsDialog/index.jsx";
import SaveDialog from "../../components/SaveDialog/index.jsx";
import { useMapDataContext } from "../../context/MapDataContext.jsx";
import logo from "../../assets/chatmap-home.png";
import SaveButton from '../../components/SaveButton';
import DownloadButton from '../../components/DownloadButton';
import { useAuth } from "../../context/AuthContext.jsx";
import { useConfigContext } from "../../context/ConfigContext.jsx";
import TagsOptions from "../../components/TagsOptions/index.jsx";

import "../../styles/home.css";

const Map = lazy(() => import("../../components/Map/index.jsx"));

function App() {
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [withPhotos, setWithPhotos] = useState(true);
  const [withVideos, setWithVideos] = useState(true);
  const [withAudios, setWithAudios] = useState(true);
  const [withText, setWithText] = useState(false);

  const { isAuthenticated } = useAuth();
  const { config } = useConfigContext();

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
  const { data, tags, mapDataDispatch } = useMapDataContext();

  const selectTagHandler = tag => {
    mapDataDispatch({
      type: 'set_filter_tag',
      payload: {tag: tag},
    });
  }

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

  function handleSaveButtonClick() {
    setSaveDialogOpen(true);
  }

  // There's data for the map!
  const dataAvailable = files && data && data.features && data.features.length > 0;

  return (
    <>
      <div className="app">
        <Header>
          { dataAvailable && <>
            <SlButton
              variant="default"
              outline
              size="small"
              onClick={handleNewUploadClick}
            >
              <SlIcon name="arrow-clockwise" slot="prefix"></SlIcon>
              <FormattedMessage
                id = "app.uploadNewFile"
                defaultMessage="New file"
              />
            </SlButton>

            <DownloadButton data={data} dataFiles={dataFiles} />

            <SaveButton onClick={handleSaveButtonClick} />

            {Object.keys(tags).length > 0 &&
              <TagsOptions
                onSelectTag={selectTagHandler}
                tags={tags}
                selectedTag={data.filterTag}
              />
            }
          </>}

          { !dataAvailable && isAuthenticated && config.ENABLE_LIVE && enableExperimental && <>
            <SlButton className="header__live-button" href="#linked" variant="default" outline size="small">
              <FormattedMessage id="app.navigation.live" defaultMessage="Live" />
            </SlButton>
          </>}
        </Header>

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
            showMessageOptions={true}
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

      <SaveDialog
        open={saveDialogOpen}
        setOpen={setSaveDialogOpen}
        data={data}
        dataFiles={dataFiles}
      />
    </>
  );
}

export default App;
