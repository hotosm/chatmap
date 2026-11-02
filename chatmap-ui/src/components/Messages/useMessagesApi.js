import { useCallback } from "react";
import { useConfigContext } from "../../context/ConfigContext.jsx";
import { apiV2, request, send } from "../../utils/apiV2.js";

// The messages of the chat groups of a map, in the API v2. Each call answers null when it fails
export default function useMessagesApi() {
    const { config } = useConfigContext();
    const api = apiV2(config.API_URL);

    // The groups of the phone of a live map: { groups: [{ id, name, enabled }], kept_days, max_kept_days }
    const readGroups = useCallback((mapId) => request(`${api}/maps/${mapId}/groups`), [api]);

    // Listen to a group or stop: { enabled, delete_messages }
    const updateGroup = useCallback(
        (mapId, groupId, change) => send('PUT', `${api}/maps/${mapId}/groups/${groupId}`, change), [api]
    );

    // How many days the map keeps the messages of its groups
    const updateKeptDays = useCallback(
        (mapId, days) => send('PUT', `${api}/maps/${mapId}/messages/kept-days`, { days }), [api]
    );

    // A page of messages, newest first: { group_id, before, before_id } narrow it or ask for the next one
    const readMessages = useCallback((mapId, params = {}) => {
        const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value));
        return request(`${api}/maps/${mapId}/messages?${query}`);
    }, [api]);

    return { readGroups, updateGroup, updateKeptDays, readMessages };
}
