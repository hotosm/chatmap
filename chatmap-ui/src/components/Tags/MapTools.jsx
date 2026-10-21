import { useMapDataContext } from "../../context/MapDataContext";

import AddPoint from "./AddPoint.jsx";
import ColorBy from "./ColorBy.jsx";
import { colorKeyOf, keepArrows, usesKeys } from "./tags.js";

/**
 * The tools of this module over the map: add a point by hand and choose the
 * key that colors it. Nothing for a map read without its keys.
 *
 * @param {object} map Ref to the MapLibre map
 * @param {object} adding Ref that is true while a point is being placed, so clicks do not open points
 * @param {boolean} show Whether whoever looks at the map can edit it
 * @param {function} onAdd Gets the feature of the point added
 */
export default function MapTools({ map, adding, show, onAdd }) {
    const { data, mapDataDispatch } = useMapDataContext();
    if (!usesKeys(data)) return null;
    const colorKey = colorKeyOf(data.keys, data.colorKey);

    return (
        <div className="mapTools" onKeyDown={keepArrows}>
            <AddPoint map={map} mapId={data.id} colorKey={colorKey} adding={adding} show={show} onAdd={onAdd} />
            <ColorBy
                keys={data.keys}
                colorKey={colorKey && colorKey.id}
                onChange={(keyId) => mapDataDispatch({ type: "set", payload: { colorKey: keyId } })}
            />
        </div>
    );
}
