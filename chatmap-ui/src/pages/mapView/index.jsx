import { useEffect, useState } from "react";
import { useParams } from 'react-router';

import { useInterval } from '../../hooks/useInterval.js';
import Header from "../header.jsx";
// import Footer from "../footer.jsx";
import { useMapDataContext } from "../../context/MapDataContext.jsx";
import { useAuth } from '../../context/AuthContext';
import Map from "../../components/Map";
import useAPI from '../../components/ChatMap/useApi.js'
import TagsOptions from "../../components/TagsOptions/index.jsx";
import ShareButton from '../../components/ShareButton';
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

  // const [footerVisible, setFooterVisible] = useState(true);
  const [mapName, setMapName] = useState(null);
  const [mapDescription, setMapDescription] = useState(null);

  // If connected, fetch map data every 1 min
  useInterval(() => { id && fetchMapData(id) }, 60000);

  const { id } = useParams();

  // Updates map data context with new map data
  useEffect(() => {
   fetchMapData(id)
  }, [id]);

  // Map Data Context: Manages map data
  const { data, tags, mapDataDispatch } = useMapDataContext();

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

  // There's data for the map!
  const dataAvailable = data && data.features && data.features.length > 0;

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
        </Header>

        {dataAvailable &&
          <>
            <Map
              showMessageOptions={mapData.owner}
              // onInteract={() => setFooterVisible(false)}
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

      {/* <Footer
        visible={footerVisible}
        className="footer__floating"
      /> */}
    </>
  );
}

export default MapView;
