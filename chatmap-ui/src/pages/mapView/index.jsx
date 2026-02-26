import { useEffect, useState } from "react";
import { useParams } from 'react-router-dom';
import { useInterval } from '../../hooks/useInterval.js';
import Header from "../header.jsx";
import Footer from "../footer.jsx";
import { useMapDataContext } from "../../context/MapDataContext.jsx";
import Map from "../../components/Map";
import useAPI from '../../components/ChatMap/useApi.js'

function MapView() {

  const {
    fetchMapData,
    mapData
  } = useAPI();

  const [footerVisible, setFooterVisible] = useState(true);

  // If connected, fetch map data every 1 min
  useInterval(() => { id && fetchMapData(id) }, 60000);

  const { id } = useParams();

  // Updates map data context with new map data
  useEffect(() => {
   fetchMapData(id)
  }, [id]);

  // Map Data Context: Manages map data
  const { data, mapDataDispatch } = useMapDataContext();

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
          dataAvailable={dataAvailable}
          mapData={data}
          showDownloadButton={false}
          title={mapData.name || "Untitled"}
        />

        {dataAvailable &&
          <Map
            onInteract={() => setFooterVisible(false)}
          />
        }
      </div>

      <Footer
        visible={footerVisible}
        className="footer__floating"
      />
    </>
  );
}

export default MapView;
