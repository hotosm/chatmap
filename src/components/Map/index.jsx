import React, { useRef, useEffect, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { osm } from './source';
import Popup from './popup';
import extent from 'turf-extent';
import './map.css';

const getMessage = (properties, dataFiles) => {
  if (properties.file && dataFiles && properties.file in dataFiles) {
    if (properties.file.endsWith("jpg") || properties.file.endsWith("jpeg")) {
      return <img className="popupImage" alt="Message attached file" src={URL.createObjectURL(dataFiles[properties.file])} />
    } else if (properties.file.endsWith("mp4")) {
      return <video controls autoplay loop className="popupImage" alt="Message attached file" src={URL.createObjectURL(dataFiles[properties.file])} />
    }
  }
  return properties.message;
}

export default function Map({ data, dataFiles }) {
    const mapContainer = useRef(null);
    const map = useRef(null);
    const [activePopupFeature, setActivePopupFeature] = useState(null);
    const popupRef = useRef(null);

    const formatDate = (properties) => {
        const d = new Date(properties.time);
        return (
          String(d.getHours()).padStart(2, '0') + ":" + 
          String(d.getMinutes()).padStart(2, '0'))
    };
      
    useEffect(() => {
      if (map.current) return;
    
      map.current = new maplibregl.Map({
        container: mapContainer.current,
        center: [0,0],
        zoom: 17,
        style: osm
      });

      map.current.on("load", () => {

        // Center the map on the first feature
        map.current.setCenter(data.features[0].geometry.coordinates)

        // Add geojson data source
        map.current.addSource('locations', {
          data: data,
          type: "geojson"
        });
        

        const bbox = extent(data);
        map.current.fitBounds(bbox, {
            padding: 50
        });

        // Change cursor on marker hover
        map.current.on('mouseenter', 'pois', () => {
          map.current.getCanvas().style.cursor = 'pointer';
        });
        map.current.on('mouseleave', 'pois', () => {
          map.current.getCanvas().style.cursor = 'inherit';
        });

        // Locations layer
        map.current.addLayer({
            'id': 'pois',
            'type': 'circle',
            'source': 'locations',
            'layout': {},
            'paint': {
                'circle-color': '#D63F40',
                'circle-radius': 10
            }
        });

        // On feature click
        map.current.on("click", "pois",  (e) => {
          setActivePopupFeature(e.features[0]);
        });
          
      });
    }, [data, popupRef]);

    // Show popup
    useEffect(() => {
      if (!map.current || !activePopupFeature) return;
      setActivePopupFeature(activePopupFeature);
      popupRef.current.addTo(map.current);
    }, [activePopupFeature]);

    return (
      <div className="map-wrap">
        <div ref={mapContainer} className="map" />
        {map.current && activePopupFeature &&
          <Popup
            longitude={activePopupFeature.geometry.coordinates[0]}
            latitude={activePopupFeature.geometry.coordinates[1]}
            popupRef={popupRef}
            closeOnMove={false}
            closeButton={true}
          >
           <div className="activePopupFeatureContent">
              <p>
                <span className="msgUsername">{activePopupFeature.properties.username}</span>
                <span className="msgDatetime">{formatDate(activePopupFeature.properties)}</span>
              </p>
              <p>
                { getMessage(activePopupFeature.properties, dataFiles) }
              </p>
            </div>
          </Popup>
        }
      </div>
    );

  }

