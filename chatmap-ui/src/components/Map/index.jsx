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
export default function Map({ dataFiles, center, zoom, className, onInteract, showMessageOptions }) {
    // A div for the map
    const mapContainer = useRef(null);
    // The Map obejct
    const map = useRef(null);
    // Map popup
    const [activePopupFeature, setActivePopupFeature] = useState(null);
    const [editingTags, setEditingTags] = useState(false);
    const popupRef = useRef(null);

    const { data, tags, mapDataDispatch } = useMapDataContext();

    useEffect(() => {
      if (map.current) return;
    
      // Creates a MapLibreGL object
      map.current = new MapGL({
        container: mapContainer.current,
        center: center || [0,0],
        zoom: zoom || 17,
        style: osm,
        minZoom: 2,
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
            padding: 50,
            maxZoom: 14
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
              'circle-color': [
                    "case",
                    ["boolean", ["get", "removed"], false],
                    '#9A969B', // --hot-color-neutral-400
                    [
                        "case",
                        ["==", ["get", "message"], "{location-only}"],
                        '#2E4873', // --hot-color-blue-600
                        '#D73F3F'  // --hot-color-red-600
                    ]
                ],
                'circle-radius': 10
            }
        });

        // Invisible layer for with a buffer for better click
        map.current.addLayer({
            'id': 'pois-clickable',
            'type': 'circle',
            'source': 'locations',
            'layout': {},
            'paint': {
                'circle-color': 'rgba(0,0,0,0)',
                'circle-radius': 25
            }
        });

        // On feature click
        map.current.on("click", "pois-clickable",  (e) => {
          const feature = {...e.features[0]};
          feature.geometry = e.features[0].geometry;
          if (feature.properties["tags"]) {
            feature.properties.tags = JSON.parse(feature.properties.tags);
          }
          setActivePopupFeature(feature);
        });

        map.current.on("click", (e) => {
          onInteract && onInteract();
        });

      });
    }, [data, popupRef]);

    // Next, prev arrows
    useEffect(() => {
      const handleKeyDownNextPrev = (event) => {
        if (!editingTags) {
          if (event.key === 'ArrowLeft') {
            const featureIndex = activePopupFeature.properties.index
            if (featureIndex > 0) {
              setActivePopupFeature(data.features[featureIndex - 1]);
            }
            map.current.flyTo({
              center: data.features[featureIndex].geometry.coordinates
            });
          } else if (event.key === 'ArrowRight') {
            const featureIndex = activePopupFeature.properties.index
            if (featureIndex < data.features.length - 1) {
              setActivePopupFeature(data.features[featureIndex + 1]);
            }
            map.current.flyTo({
              center: data.features[featureIndex].geometry.coordinates
            });
          }
        }
      };
      window.addEventListener("keydown", handleKeyDownNextPrev);
      return () => {
        window.removeEventListener("keydown", handleKeyDownNextPrev);
      };
    }, [editingTags, activePopupFeature]);

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

    // Filter by tag
    useEffect(() => {
      if (!map.current || !activePopupFeature) return;
      if (data.filterTag) {
        setActivePopupFeature(null);
        popupRef.current.remove()
      }
    }, [data.filterTag])

    // Tag handlers

    const handleAddTag = (tag, feature) => {
      if (!feature.properties.tags) {
        feature.properties.tags = [];
      }
      feature.properties.tags.push(tag);
      handleChange(feature);
      setEditingTags(false);
    };

    const handleRemoveTag = (tag, feature) => {
        feature.properties.tags = feature.properties.tags.filter(x => x != tag);
        handleChange(feature);
        setEditingTags(false);
    }

    const handleRemoveMessage = (feature) => {
      feature.properties.removed = !feature.properties.removed;
      handleChange(feature);
    }

    const handleChange = (feature) => {
      mapDataDispatch({
        type: "update_feature_props",
        payload: {
            ...feature,
            properties: feature.properties,
            id: feature.properties.id
        }
      });
      setActivePopupFeature(feature);
    }

    return (
      <div className="map-wrap">
        <div ref={mapContainer} className={["map", className].join(" ")} />
        {map.current && activePopupFeature &&
          <Popup
            popupRef={popupRef}
            feature={activePopupFeature}
            dataFiles={dataFiles}
            onAddTag={handleAddTag}
            onRemoveTag={handleRemoveTag}
            onRemoveMessage={handleRemoveMessage}
            allTags={Object.keys(tags)}
            showMessageOptions={showMessageOptions}
          />
        }
      </div>
    );

  }

