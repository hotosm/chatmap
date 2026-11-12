import React, {useRef, useEffect, useState} from 'react';
import {Map as MapGL, GeolocateControl} from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import {osm} from './source';
import Popup from './popup';
import extent from 'turf-extent';
import {useMapDataContext} from '../../context/MapDataContext';
import useAPI from '../../components/ChatMap/useApi.js'
import {MapTools, useMapTags} from '../Tags';
import {BackgroundControl} from "./controls.jsx";

// The room a popup takes at the right of its point, and half its height
const POPUP_ROOM = { width: 330, height: 160, margin: 16 };

/**
 *
 * @param {object} dataFiles Files data
 * @param {function} onSelect Gets the point whose popup is open, or null when it closes
 * @param {object} cover Pixels a panel covers over the map, { right, bottom }: the point chosen is kept out of them
 * @returns {React.ReactElement} Map component
 */
export default function Map({dataFiles, center, zoom, className, onInteract, showMessageOptions, onSelect, cover}) {
    // A div for the map
    const mapContainer = useRef(null);
    // The Map obejct
    const map = useRef(null);
    // Map popup
    const [activePopupFeature, setActivePopupFeature] = useState(null);
    const [editingTags, setEditingTags] = useState(false);
    const popupRef = useRef(null);
    const {
        removePoint,
        updatePointTags
    } = useAPI();

    const {data, tags, mapDataDispatch} = useMapDataContext();
    // The values of the keys of the map, when it has them; it changes every minute, as values expire
    const mapTags = useMapTags(data);

    const dataRef = useRef(data);
    dataRef.current = data;
    // True while a point is being added by hand
    const addingPoint = useRef(false);

    const showFeature = (feature) => {
        if (feature) setActivePopupFeature(feature);
    };

    // Color of a point: by kind of message, gray when removed
    const pointColor = [
        "case",
        ["boolean", ["get", "removed"], false],
        '#9A969B', // --hot-color-neutral-400
        [
            "case",
            ["any", ["to-boolean", ["get", "file"]], ["to-boolean", ["get", "media"]]],
            '#D73F3F',  // --hot-color-red-600
            '#2E4873', // --hot-color-blue-600
        ]
    ];

    useEffect(() => {
        if (map.current) return;

        // Creates a MapLibreGL object, already showing all the points: it does not
        // open close to one of them and then fly out to the rest
        const points = data.features && data.features.length > 0;
        map.current = new MapGL({
            container: mapContainer.current,
            ...(points ?
                { bounds: extent(data), fitBoundsOptions: { padding: 50, maxZoom: 14 } } :
                { center: center || [0, 0], zoom: zoom || 17 }),
            style: osm,
            minZoom: 2,
        });

        map.current.on("load", async () => {

            // Add background control
            map.current.addControl(new BackgroundControl());

            // Add location control
            let geolocate = new GeolocateControl({
                positionOptions: {
                    enableHighAccuracy: true
                },
                trackUserLocation: true
            });
            // Add the control to the map.
            map.current.addControl(geolocate);

            // Add geojson data source
            map.current.addSource('locations', {
                data: mapTags.shown(data),
                type: "geojson"
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
                    'circle-color': pointColor,
                    'circle-radius': 10
                }
            });

            mapTags.paint(map.current, 'pois', pointColor);

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
            map.current.on("click", "pois-clickable", (e) => {
                if (addingPoint.current) return;
                const clickedId = e.features[0].properties.id;
                showFeature(dataRef.current.features.find((feature) => feature.properties.id === clickedId));
            });

            map.current.on("click", () => {
                onInteract && onInteract();
            });

        });
    }, [data, popupRef]);

    // Next, prev arrows
    useEffect(() => {
        const handleKeyDownNextPrev = (event) => {
            if (editingTags || !activePopupFeature) return;

            const step = event.key === 'ArrowLeft' ? -1 : event.key === 'ArrowRight' ? 1 : 0;
            if (!step) return;

            const features = dataRef.current.features;
            const currentIndex = features.findIndex(
                (feature) => feature.properties.id === activePopupFeature.properties.id
            );
            const next = features[currentIndex + step];
            if (!next) return;

            showFeature(next);
            map.current.flyTo({center: next.geometry.coordinates});
        };
        window.addEventListener("keydown", handleKeyDownNextPrev);
        return () => {
            window.removeEventListener("keydown", handleKeyDownNextPrev);
        };
    }, [editingTags, activePopupFeature]);

    useEffect(() => {
        if (map.current.getSource("locations")) {

            // Add geojson data source
            if (data.filterTag !== null) {
                // The filter can also be a value of a key of the map
                const byValue = mapTags.filter(data.filterTag);
                {
                    map.current.getSource('locations').setData(mapTags.shown({
                        ...data,
                        features: data.features.filter(feature =>
                            byValue ? byValue(feature)
                                : data.filterTag !== undefined ?
                                    feature.properties.tags && feature.properties.tags.split(",").indexOf(data.filterTag) > -1
                                    : !feature.properties.tags
                        )
                    }));
                }
            } else {
                map.current.getSource('locations').setData(mapTags.shown(data));
            }

            mapTags.paint(map.current, 'pois', pointColor);

        }
    }, [data, mapTags]);

    // Show popup
    useEffect(() => {
        if (!map.current || !activePopupFeature) return;
        setActivePopupFeature(activePopupFeature);
        popupRef.current.addTo(map.current);
    }, [activePopupFeature]);

    // The popup shows its point as the map has it now, after the map is read again
    useEffect(() => {
        if (!activePopupFeature) return;
        const now = data.features.find((feature) => feature.properties.id === activePopupFeature.properties.id);
        if (now && now !== activePopupFeature) setActivePopupFeature(now);
    }, [data]);

    // A point chosen under a panel moves out of it, with room for its popup at its right
    useEffect(() => {
        if (!map.current || !activePopupFeature || !cover) return;
        const {x, y} = map.current.project(activePopupFeature.geometry.coordinates);
        const {width, height} = map.current.getContainer().getBoundingClientRect();
        const dx = Math.min(Math.max(0, x - (width - (cover.right || 0) - POPUP_ROOM.width)), x - POPUP_ROOM.margin);
        const dy = Math.min(Math.max(0, y - (height - (cover.bottom || 0) - POPUP_ROOM.height)), y - POPUP_ROOM.margin);
        if (dx > 0 || dy > 0) map.current.panBy([Math.max(dx, 0), Math.max(dy, 0)]);
    }, [activePopupFeature, cover]);

    // Tell which point is chosen; when its popup closes, none is
    const onSelectRef = useRef(onSelect);
    onSelectRef.current = onSelect;
    useEffect(() => {
        onSelectRef.current && onSelectRef.current(activePopupFeature);
        const popup = popupRef.current;
        if (!popup || !activePopupFeature) return;
        const closed = () => setActivePopupFeature(null);
        popup.on("close", closed);
        return () => popup.off("close", closed);
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
        const oldTags = (feature.properties.tags || "").split(",").filter(x => x);

        oldTags.push(tag);

        feature.properties.tags = oldTags.join(",");
        updatePointTags(feature.properties.id, feature.properties.tags)
        handleChange(feature);
        setEditingTags(false);
    };

    const handleRemoveTag = (tag, feature) => {
        feature.properties.tags = (feature.properties.tags || "")
            .split(",").filter(x => x).filter(x => x != tag).join(",");
        updatePointTags(feature.properties.id, feature.properties.tags)
        handleChange(feature);
        setEditingTags(false);
    }

    const handleAddPoint = (feature) => {
        mapDataDispatch({
            type: "set",
            payload: {features: [...dataRef.current.features, feature]}
        });
        showFeature(feature);
    }

    const handleRemoveMessage = async (feature) => {
        await removePoint(feature.properties.id);
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
            {/* The map and its controls are not mirrored in right to left languages */}
            <div ref={mapContainer} dir="ltr" className={["map", className].join(" ")}/>
            <MapTools map={map} adding={addingPoint} show={showMessageOptions} onAdd={handleAddPoint}/>
            {map.current && activePopupFeature &&
                <Popup
                    popupRef={popupRef}
                    feature={activePopupFeature}
                    dataFiles={dataFiles}
                    onAddTag={handleAddTag}
                    onRemoveTag={handleRemoveTag}
                    onRemoveMessage={handleRemoveMessage}
                    allTags={Object.keys(tags)}
                    pointTags={mapTags.point}
                    onChange={handleChange}
                    showMessageOptions={showMessageOptions}
                />
            }
        </div>
    );

}
