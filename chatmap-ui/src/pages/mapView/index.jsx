import { useEffect, useState } from "react";
import { useParams } from 'react-router';
import { FormattedMessage } from "react-intl";

import SlButton from "@shoelace-style/shoelace/dist/react/button/index.js";
import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";

import { useInterval } from '../../hooks/useInterval.js';
import Header from "../header.jsx";
import { useMapDataContext } from "../../context/MapDataContext.jsx";
import { useAuth } from '../../context/AuthContext';
import Map from "../../components/Map";
import useAPI from '../../components/ChatMap/useApi.js'
import TagsOptions from "../../components/TagsOptions/index.jsx";
import ShareButton from '../../components/ShareButton';
import FileUpload from "../../components/FileUpload/index.jsx";
import useFileManager from "../../components/FileUpload/useFileManager.js";
import SettingsDialog from "../../components/SettingsDialog/index.jsx";
import useContentMerger from "../../components/ChatMap/useContentMerger.js";
import UpdateButton from "../../components/UpdateButton/index.jsx";
import EditMapDialog from '../../components/EditMapDialog/index.jsx';
import InfoMapDialog from '../../components/InfoMapDialog/index.jsx';

function MapView() {

  const [editMapDialogOpen, setEditMapDialogOpen] = useState(false);
  const [infoMapDialogOpen, setInfoMapDialogOpen] = useState(false);
  const { isAuthenticated } = useAuth();

  const {
    fetchMapData,
    mapData
  } = useAPI();

  // File management stuff
  const [
    handleFiles, handleDataFile, resetFileManager, dataFiles, files,
  ] = useFileManager();
  const { data, tags, mapDataDispatch } = useMapDataContext();
  const [withPhotos, setWithPhotos] = useState(true);
  const [withVideos, setWithVideos] = useState(true);
  const [withAudios, setWithAudios] = useState(true);
  const [withText, setWithText] = useState(false);
  const [settingsDialogOpen, setSettingsDialogOpen] = useState();
  const [newMapData, resetMerger] = useContentMerger({
    files, withPhotos, withVideos, withAudios, withText,
  });

  const [mapName, setMapName] = useState(null);
  const [mapDescription, setMapDescription] = useState(null);

  const { id } = useParams();

  // If connected, fetch map data every 1 min
  useInterval(() => { id && mapData && mapData.is_live && fetchMapData(id) }, 60000);

  // Updates map data context with new map data
  useEffect(() => {
   fetchMapData(id)
  }, [id]);

  const selectTagHandler = tag => {
    mapDataDispatch({
      type: 'set_filter_tag',
      payload: {tag: tag},
    });
  }

  // Updates map data context with new map data
  useEffect(() => {
    mapDataDispatch({
      type: 'set',
      payload: mapData,
    });
    if (mapData.id) {
      history.replaceState(null, '', `/#map/${mapData.id}`);
    }
  }, [mapData]);

  useEffect(() => {
    if (newMapData.features.length > 0) {
      setSettingsDialogOpen(true);
    }

    const alreadyExists = {};

    for (let feature of data.features) {
      if (!feature._temporary) {
        alreadyExists[feature.geometry.coordinates.join(':')] = true;
      }
    }

    mapDataDispatch({
      type: 'add_tmp_features',
      payload: {
        ...newMapData,
        features: newMapData.features.filter((f) => {
          return !alreadyExists[f.geometry.coordinates.join(':')];
        }),
      },
    });
  }, [newMapData]);

  function handleDiscard() {
    mapDataDispatch({
      type: 'add_tmp_features',
      payload: {
        ...newMapData,
        features: [],
      },
    });
  }

  // There's data for the map!
  const dataAvailable = data && data.features && data.features.length > 0;
  const hasNewData = data && data.features.filter((f) => f._temporary).length > 0;

  return (
    <>
      <div className="app">
        <Header
          title={mapName || mapData.name}
          pageTitle={mapName || mapData.name}
          onTitleClick={() => isAuthenticated ? setEditMapDialogOpen(true) : setInfoMapDialogOpen(true)}
        >
          {Object.keys(tags).length > 0 &&
            <TagsOptions
              onSelectTag={selectTagHandler}
              tags={tags}
              selectedTag={data.filterTag}
            />
          }
          { dataAvailable && mapData.owner && <>
            <ShareButton
              sharing={data.sharing}
              id={mapData.id}
            />
          </>}
          { !mapData.is_live && <>
            <FileUpload
              onDataFileLoad={handleDataFile}
              onFilesLoad={handleFiles}
            >
              <SlButton size="small">
                <SlIcon name="file-earmark-plus-fill" slot="prefix" />
                <FormattedMessage id="app.map.addNew" defaultMessage="Add new data" />
              </SlButton>
            </FileUpload>

            { hasNewData && <>
              <UpdateButton
                mapData={mapData}
                data={data}
                dataFiles={dataFiles}
                onUpdate={() => fetchMapData(id)}
              />

              <SlButton size="small" onClick={handleDiscard}>
                <FormattedMessage id="app.map.discard" defaultMessage="Discard" />
              </SlButton>
            </> }
          </>}
        </Header>

        {dataAvailable &&
          <>
            <Map
              showMessageOptions={mapData.owner}
              dataFiles={dataFiles}
            />
            <EditMapDialog
              mapData={{
                ...mapData,
                name: mapName || mapData.name,
                description: mapDescription || mapData.description
              }}
              open={editMapDialogOpen}
              setOpen={setEditMapDialogOpen}
              onSuccess={(response) => {
                setMapName(response.name);
                setMapDescription(response.description);
              }}
            />
            <InfoMapDialog
              mapData={{
                ...mapData,
                name: mapName || mapData.name,
                description: mapDescription || mapData.description
              }}
              open={infoMapDialogOpen}
              setOpen={setInfoMapDialogOpen}
            />
          </>
        }
      </div>

      <SettingsDialog
        open={settingsDialogOpen}
        setOpen={setSettingsDialogOpen}
        numFeatures={newMapData.features.length}
        sources={newMapData._sources}
        withPhotos={withPhotos} setWithPhotos={setWithPhotos}
        withVideos={withVideos} setWithVideos={setWithVideos}
        withAudios={withAudios} setWithAudios={setWithAudios}
        withText={withText} setWithText={setWithText}
      ></SettingsDialog>
    </>
  );
}

export default MapView;
