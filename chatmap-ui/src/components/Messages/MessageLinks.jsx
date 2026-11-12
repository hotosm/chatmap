import { useState } from "react";
import { FormattedMessage } from "react-intl";

import { ValueChip } from "../Tags";
import { liveLinks } from "./messages.js";

/**
 * What a message gave to places: "→ North access · Closed · Undo", one row
 * per link that was not undone.
 *
 * @param {object} mapData The map, to name the places and their values
 * @param {function} onUndo Gets the message and the link; answers null when it is not undone
 */
export default function MessageLinks({ message, mapData, onUndo }) {
    const [busy, setBusy] = useState(null);
    const [failed, setFailed] = useState(false);
    const links = liveLinks(message);
    if (links.length === 0) return null;

    const placeName = (pointId) => {
        const feature = (mapData.features || []).find((item) => item.properties.id === pointId);
        return feature ? feature.properties.message : "";
    };
    const valueOf = (link) => {
        const key = (mapData.keys || []).find((item) => item.id === link.key_id);
        return (key && key.values.find((item) => item.id === link.value_id)) || { value: link.value };
    };

    const undo = async (link) => {
        setBusy(link.change_id);
        const undone = await onUndo(message, link);
        setBusy(null);
        setFailed(!undone);
    };

    return (
        <ul className="messageLinks">
            { links.map((link) =>
                <li key={link.change_id} className="messageLinks__link">
                    <span aria-hidden="true" className="messageLinks__arrow">→</span>
                    <strong>{placeName(link.point_id)}</strong>
                    <ValueChip value={valueOf(link)} />
                    <button
                        type="button"
                        className="messageLinks__undo"
                        disabled={busy === link.change_id}
                        onClick={() => undo(link)}
                    >
                        <FormattedMessage id="app.messages.undo" defaultMessage="Undo" />
                    </button>
                </li>
            )}
            { failed &&
                <li className="messageLinker__notice messageLinker__notice--error" role="alert">
                    <FormattedMessage id="app.messages.notUndone" defaultMessage="It could not be undone. Try again." />
                </li>
            }
        </ul>
    );
}
