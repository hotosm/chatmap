import { lazy, useState, useEffect } from "react";
import { FormattedMessage } from "react-intl";

import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';
import SlIcon from '@shoelace-style/shoelace/dist/react/icon/index.js';

import ConfirmDialog from "../../components/ConfirmDialog";
import DownloadButton from '../../components/DownloadButton';
import FileUploadSection from './fileUpload.section.jsx';
import Footer from "../footer.jsx";
import Header from "../header.jsx";
import SaveButton from '../../components/SaveButton';
import SaveDialog from "../../components/SaveDialog/index.jsx";
import SettingsDialog from "../../components/SettingsDialog/index.jsx";
import TagsOptions from "../../components/TagsOptions/index.jsx";
import logo from "../../assets/chatmap-home.png";
import useContentMerger from "../../components/ChatMap/useContentMerger.js";
import useFileManager from "../../components/FileUpload/useFileManager.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { useConfigContext } from "../../context/ConfigContext.jsx";
import { useMapDataContext } from "../../context/MapDataContext.jsx";

import "../../styles/home.css";

const Map = lazy(() => import("../../components/Map/index.jsx"));

function App() {
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [withPhotos, setWithPhotos] = useState(true);
  const [withVideos, setWithVideos] = useState(true);
  const [withAudios, setWithAudios] = useState(true);
  const [withText, setWithText] = useState(false);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);

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

  function handleSaveButtonNoSession() {
    setConfirmDialogOpen(true);
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

            <SaveButton onClick={isAuthenticated ? handleSaveButtonClick : handleSaveButtonNoSession} />

            {Object.keys(tags).length > 0 &&
              <TagsOptions
                onSelectTag={selectTagHandler}
                tags={tags}
                selectedTag={data.filterTag}
              />
            }
          </>}

          { !dataAvailable && isAuthenticated && config.ENABLE_LIVE && <>
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

      <ConfirmDialog
        open={confirmDialogOpen}
        setOpen={setConfirmDialogOpen}
        onConfirm={() => {
          console.log('acá');
          const returnTo = encodeURIComponent(window.location.href);
          window.location.href = `${config.LOGIN_URL}?return_to=${returnTo}`;
        }}
        title={{id: "app.home.saveConfirmDialog.title", defaultMessage: "Wait"}}
        okText={{id: "app.home.saveConfirmDialog.okText", defaultMessage: "Log in"}}
      >
        <p>
          <FormattedMessage id="app.home.saveConfirmDialog.text1" defaultMessage="You need to log in to save a map. You will have to upload your export again afterwards." />
        </p>

        <p>
          <FormattedMessage id="app.home.saveConfirmDialog.text2" defaultMessage="If you made any changes, like tagging points, we recommend downloading your progress now and upload it again after logging in." />
        </p>

        <DownloadButton data={data} dataFiles={dataFiles} />
      </ConfirmDialog>
    </>
  );
}

export default App;
