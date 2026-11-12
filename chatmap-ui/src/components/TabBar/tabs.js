/**
 * The tabs of the dashboard of a map on a phone: its map and the messages of
 * its groups. The settings of the design have no page of their own yet, so
 * they are not a tab. With one tab there is nowhere to go: no tab bar.
 *
 * @param {string} mapId The map
 * @param {boolean} withMessages Whether its messages are shown (see messagesOn)
 * @param {string} path The path of the current page, to know which tab it is
 * @returns {object[]} {id, path, icon, active}, or none
 */
export const mapTabs = ({ mapId, withMessages, path }) => {
    if (!mapId) return [];
    const tabs = [{ id: "map", path: `/map/${mapId}`, icon: "map" }];
    if (withMessages) tabs.push({ id: "messages", path: `/map/${mapId}/messages`, icon: "chat-square-text" });
    if (tabs.length < 2) return [];
    return tabs.map((tab) => ({ ...tab, active: tab.path === path }));
};
