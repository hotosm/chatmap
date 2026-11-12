import { useIntl } from "react-intl";
import { useLocation } from "react-router";

import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";

import { useConfigContext } from "../../context/ConfigContext.jsx";
import { groupMessagesOn, messagesOn, pageOf } from "../Messages";
import { usesKeys } from "../Tags";
import { mapTabs } from "./tabs.js";
import "./tabBar.css";

// The name of each tab
const LABELS = {
    map: { id: "app.tabBar.map", defaultMessage: "Map" },
    messages: { id: "app.messages.title", defaultMessage: "Messages" },
};

/**
 * The tabs at the bottom of the dashboard of a map, only on a phone: they
 * take the place of the nav of the header and of the links between the map
 * and its messages (tabBar.css). Nothing when the map has only one of them.
 *
 * @param {object} mapData The map
 * @param {object} data What is shown of it, to know if it is read with its keys
 */
export default function TabBar({ mapData, data }) {
    const intl = useIntl();
    const { config } = useConfigContext();
    const { pathname } = useLocation();
    const withMessages = groupMessagesOn(config) && messagesOn(mapData, usesKeys(data));
    const tabs = mapTabs({ mapId: mapData && mapData.id, withMessages, path: pathname });
    if (tabs.length === 0) return null;

    return (
        <nav className="tabBar" aria-label={intl.formatMessage({ id: "app.tabBar.label", defaultMessage: "Sections of the map" })}>
            <ul className="tabBar__tabs">
                { tabs.map((tab) => (
                    <li key={tab.id}>
                        <a
                            className="tabBar__tab"
                            href={pageOf(tab.path)}
                            aria-current={tab.active ? "page" : undefined}
                        >
                            <SlIcon name={tab.icon} aria-hidden="true" />
                            <span>{intl.formatMessage(LABELS[tab.id])}</span>
                        </a>
                    </li>
                )) }
            </ul>
        </nav>
    );
}
