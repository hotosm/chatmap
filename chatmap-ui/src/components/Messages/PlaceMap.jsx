import { useEffect, useRef } from "react";
import { Map as MapGL, Marker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import { osm } from "../Map/source";
import { boundsOf } from "./linkStates.js";

// A marker of a class of linkStates.css at [lat, lon]
const markerAt = (map, coords, className) => {
    const element = document.createElement("div");
    element.className = className;
    return new Marker({ element }).setLngLat([coords[1], coords[0]]).addTo(map);
};

/**
 * A small map of where a message was sent from and, when there is one, the
 * place it may be about: both in sight. Only to look at, unless onPoint is
 * given: then a click on it points where a new place goes, for a message
 * that does not say where it was sent from, starting from the places the
 * map already has.
 *
 * @param {array|null} from [lat, lon] of the message
 * @param {array|null} place [lat, lon] of the place, or of the point chosen
 * @param {array} around [[lat, lon]] of the places of the map, to start from when there is no `from`
 * @param {function} onPoint Gets the [lat, lon] clicked; without it the map is only to look at
 */
export default function PlaceMap({ from = null, place = null, around = [], onPoint = null }) {
    const container = useRef();
    const map = useRef(null);
    const markers = useRef([]);
    const pointed = useRef(onPoint);
    pointed.current = onPoint;

    useEffect(() => {
        const start = from || around[0] || [0, 0];
        map.current = new MapGL({
            container: container.current,
            style: osm,
            center: [start[1], start[0]],
            zoom: from || around.length ? 15 : 1,
            interactive: Boolean(onPoint),
            attributionControl: { compact: true },
        });
        const bounds = !from && boundsOf(around);
        if (bounds) map.current.fitBounds(bounds, { padding: 32, maxZoom: 16, duration: 0 });
        map.current.on("click", (event) => pointed.current && pointed.current([event.lngLat.lat, event.lngLat.lng]));
        return () => {
            map.current.remove();
            map.current = null;
        };
    }, []);

    const [fromLat, fromLon] = from || [];
    const [placeLat, placeLon] = place || [];
    useEffect(() => {
        markers.current.forEach((marker) => marker.remove());
        markers.current = [];
        if (from) markers.current.push(markerAt(map.current, from, "placeMap__from"));
        if (place) markers.current.push(markerAt(map.current, place, "placeMap__place"));
        // Choosing a point, the map stays where the person moved it
        if (onPoint || !from) return;
        if (!place) {
            map.current.jumpTo({ center: [fromLon, fromLat], zoom: 15 });
            return;
        }
        map.current.fitBounds(boundsOf([from, place]), { padding: 32, maxZoom: 16, duration: 0 });
    }, [fromLat, fromLon, placeLat, placeLon]);

    return <div className={`placeMap ${onPoint ? "placeMap--choosing" : ""}`} ref={container} />;
}
