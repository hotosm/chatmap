import { useCallback } from "react";
import { useConfigContext } from "../../context/ConfigContext.jsx";
import { apiV2, request, send, sendWithStatus } from "../../utils/apiV2.js";

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

    // A page of messages, newest first: { group_id, state, before, before_id } narrow it or ask for the next one
    const readMessages = useCallback((mapId, params = {}) => {
        const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value));
        return request(`${api}/maps/${mapId}/messages?${query}`);
    }, [api]);

    // Give a point the value of a key a message tells: { point_id, key_id, value_id | value }.
    // It answers { status, answer }, to tell why it failed
    const linkMessage = useCallback(
        (messageId, link) => sendWithStatus('POST', `${api}/messages/${messageId}/links`, link), [api]
    );

    // The changes of the tags of a point, newest first; the ones from messages carry message_id and message_text
    const readPointHistory = useCallback((pointId) => request(`${api}/points/${pointId}/history`), [api]);

    // Undo a link (the change it made), or bring it back
    const setLinkUndone = useCallback(
        (changeId, undone) => send('POST', `${api}/tag-changes/${changeId}/${undone ? "undo" : "restore"}`), [api]
    );

    // Dismiss a message, or bring it back
    const setDismissed = useCallback(
        (messageId, dismissed) => send('PUT', `${api}/messages/${messageId}`, { dismissed }), [api]
    );

    return {
        readGroups, updateGroup, updateKeptDays, readMessages, linkMessage, setLinkUndone, setDismissed, readPointHistory,
    };
}
