import React, { useRef, useEffect, useState } from 'react';
import { Map as MapGL } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { osm } from './source';
import Popup from './popup';
import extent from 'turf-extent';
import { useMapDataContext } from '../../context/MapDataContext';

/**
 *
 * @param {object} dataFiles Files data
 * @returns {React.ReactElement} Map component
 */
export default function Map({ dataFiles }) {
    // A div for the map
    const mapContainer = useRef(null);
    // The Map obejct
    const map = useRef(null);
    // Map popup
    const [activePopupFeature, setActivePopupFeature] = useState(null);
    const [featureIndex, setFeatureIndex] = useState(0);
    const popupRef = useRef(null);

    const { data, mapDataDispatch } = useMapDataContext();

    useEffect(() => {
      if (map.current) return;
    
      // Creates a MapLibreGL object
      map.current = new MapGL({
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

        // Fit map bounds on data extent
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
          const feature = {...e.features[0]};
          feature.geometry = e.features[0].geometry;
          if (feature.properties["tags"]) {
            feature.properties.tags = JSON.parse(feature.properties.tags);
          }
          data.features.forEach((item, index) => {
            if (feature.properties.id == item.properties.id) {
              setFeatureIndex(index);
            }
          });
          
          setActivePopupFeature(feature);
        });

      });
    }, [data, popupRef]);

    // Next, prev arrows
    useEffect(() => {
      const handleKeyDown = (event) => {
        if (event.key === 'ArrowLeft') {
          if (featureIndex > 0) {
            setActivePopupFeature(data.features[featureIndex - 1]);
            setFeatureIndex(featureIndex - 1);  
          }
        } else if (event.key === 'ArrowRight') {
          if (featureIndex < data.features.length - 1) {
            setActivePopupFeature(data.features[featureIndex + 1]);
            setFeatureIndex(featureIndex + 1);
          }
        }
      };
      map.current.flyTo({
        center: data.features[featureIndex].geometry.coordinates
      });
      window.addEventListener("keydown", handleKeyDown);
      return () => {
        window.removeEventListener("keydown", handleKeyDown);
      };
    }, [featureIndex]); 

    useEffect(() => {
      if (map.current.getSource("locations")) {
        // Add geojson data source
        if (data.filterTag) {
          {
            map.current.getSource('locations').setData({
              ...data,
              features: [
                ...data.features.filter(feature => 
                  feature.properties.tags && feature.properties.tags.indexOf(data.filterTag) > -1
                )
              ]
            });
          }
        } else {
          map.current.getSource('locations').setData(data);
        }
        
      }
    }, [data]);

    // Show popup
    useEffect(() => {
      if (!map.current || !activePopupFeature) return;
      setActivePopupFeature(activePopupFeature);
      popupRef.current.addTo(map.current);
    }, [activePopupFeature]);

    // Tag handlers

    const handleAddTag = (tag, feature) => {
      if (!feature.properties.tags) {
        feature.properties.tags = [];
      }
      feature.properties.tags.push(tag);
      handleChange(feature);
    };

    const handleRemoveTag = (tag, feature) => {
        feature.properties.tags = feature.properties.tags.filter(x => x != tag);
        handleChange(feature);
    }

    const handleChange = (feature) => {
      mapDataDispatch({
        type: "update_feature_props",
        payload: {
            properties: feature.properties,
            id: feature.properties.id
        }
      });
      setActivePopupFeature(feature);
    }

    return (
      <div className="map-wrap">
        <div ref={mapContainer} className="map" />
        {map.current && activePopupFeature &&
          <Popup
            popupRef={popupRef}
            feature={activePopupFeature}
            dataFiles={dataFiles}
            onAddTag={handleAddTag}
            onRemoveTag={handleRemoveTag}
          />
        }
      </div>
    );

  }

