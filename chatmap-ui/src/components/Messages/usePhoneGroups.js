import { useEffect, useState } from "react";

import useMessagesApi from "./useMessagesApi.js";

/**
 * The groups of the phone of a map, with the ones it listens to, and how
 * long it keeps their messages, as the API answers them: null while they
 * are read, and without groups (failed) when they cannot be.
 *
 * @param {string} mapId The map
 */
export default function usePhoneGroups(mapId) {
    const { readGroups } = useMessagesApi();
    const [phone, setPhone] = useState(null);

    useEffect(() => {
        let current = true;
        setPhone(null);
        readGroups(mapId).then((answer) => current && setPhone(answer || { groups: [], failed: true }));
        return () => { current = false; };
    }, [mapId, readGroups]);

    return [phone, setPhone];
}
