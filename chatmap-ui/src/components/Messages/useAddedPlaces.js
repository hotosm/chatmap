import { useCallback, useMemo, useState } from "react";

import { useTagsApi } from "../Tags";
import { placeAt } from "./linkStates.js";

/**
 * The map as the messages page reads it, with the places added from its
 * messages while the page is open: the map was read once, and a new place
 * has to be there to link messages to it.
 *
 * @returns {array} [mapData, addPlace]; addPlace(name, coords) answers the
 *   place added as placesOf lists it ({ id, name, meters: 0 }), or null when the API does not take it
 */
export default function useAddedPlaces(mapData) {
    const { createPoint } = useTagsApi();
    const [added, setAdded] = useState([]);

    // Only the ones of this map that it does not have yet, if it is read again
    const withAdded = useMemo(() => {
        const read = new Set((mapData.features || []).map((feature) => feature.properties.id));
        const missing = added.filter((place) => place.mapId === mapData.id && !read.has(place.feature.properties.id));
        return missing.length ?
            { ...mapData, features: [...(mapData.features || []), ...missing.map((place) => place.feature)] } : mapData;
    }, [mapData, added]);

    const addPlace = useCallback(async (name, coords) => {
        const { request, featureOf } = placeAt(name, coords);
        const created = await createPoint(mapData.id, request);
        if (!created) return null;
        // The API names the point: the same place given twice is the one it had
        setAdded((places) => [...places, { mapId: mapData.id, feature: featureOf(created.id) }]);
        return { id: created.id, name, meters: 0 };
    }, [createPoint, mapData.id]);

    return [withAdded, addPlace];
}
