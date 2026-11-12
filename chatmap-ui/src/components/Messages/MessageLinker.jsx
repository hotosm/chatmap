import { useMemo, useRef, useState } from "react";
import { FormattedMessage } from "react-intl";

import { KeyValues } from "../Tags";
import { LinkOutcome } from "./LinkStates.jsx";
import PlacePicker from "./PlacePicker.jsx";
import { FAILED, TWICE, linkOutcome, statusKeyOf } from "./linkStates.js";
import { coordsOf, liveLinks, placesOf } from "./messages.js";

/**
 * Links a message to a place of the map: "Choose place", then "Choose
 * status" with the values of its keys. Picking a value gives it to the
 * place at the time of the message and, when that does not change what the
 * place shows (it had something newer, the value already expired, the
 * message already gave it) or it could not be done, says so in a bar
 * inside the card (see LinkOutcome).
 *
 * @param {object} mapData The map, with its points (features) and keys
 * @param {function} onLink Gets the message and the change; answers { status, answer } (see useMessageActions)
 * @param {function} onUndo Gets the message and a link; answers null when it is not undone
 * @param {function} onReload Reads the messages again, after a link the API did not take
 * @param {function} onCreatePlace Gets a name and [lat, lon]; answers the new place, or null (see useAddedPlaces)
 * @param {array} groupPointIds The places the group of the message always speaks of, if its owner said so:
 *   one comes chosen, two come as shortcuts, always saying they come from the group
 */
export default function MessageLinker({
    message, mapData, keys, onLink, onUndo, onReload, onCreatePlace, groupPointIds = [],
}) {
    const dropdown = useRef();
    const [place, setPlace] = useState(null);
    const [busy, setBusy] = useState(false);
    // What the last link did, with the name of its place, or null
    const [outcome, setOutcome] = useState(null);
    const coords = useMemo(() => coordsOf(message.location), [message.location]);
    const places = useMemo(() => placesOf(mapData.features, coords), [mapData.features, coords]);
    const statusKey = useMemo(() => statusKeyOf(mapData.keys), [mapData.keys]);
    // The places of the group, when its owner said it always speaks of them
    const ofGroup = useMemo(
        () => groupPointIds.map((id) => places.find((item) => item.id === id)).filter(Boolean), [groupPointIds, places],
    );
    const byGroup = !place && ofGroup.length === 1;
    const chosen = place || (byGroup ? ofGroup[0] : null);

    const pick = async (keyId, change) => {
        setOutcome(null);
        const key = keys.find((item) => item.key.id === keyId).key;
        const value = (key.values || []).find((item) => item.id === change.value_id) || null;
        const said = { place: chosen.name };
        // The same message giving the same value to the same place says nothing new
        const twice = liveLinks(message).some((link) =>
            link.point_id === chosen.id && link.key_id === keyId &&
            (change.value_id ? link.value_id === change.value_id : link.value === change.value)
        );
        if (twice) {
            dropdown.current && dropdown.current.hide();
            setOutcome({ ...said, kind: TWICE, value: value ? value.value : change.value });
            return;
        }
        setBusy(true);
        const { status, answer } = await onLink(message, { point_id: chosen.id, key_id: keyId, ...change });
        setBusy(false);
        if (!answer) {
            setOutcome({ ...said, kind: FAILED, status });
            return;
        }
        dropdown.current && dropdown.current.hide();
        const done = linkOutcome({ answer, key, value, sentAt: message.sent_at });
        setOutcome(done && { ...said, ...done });
        setPlace(null);
    };

    // Undone from its bar, the bar goes away with it
    const undo = async (link) => {
        const undone = await onUndo(message, link);
        if (undone) setOutcome(null);
        return undone;
    };

    return (
        <div className="messageLinker">
            <div className="messageLinker__pickers">
                <PlacePicker
                    places={places}
                    place={chosen}
                    onPick={setPlace}
                    disabled={busy}
                    coords={coords}
                    features={mapData.features}
                    statusKey={statusKey}
                    onCreate={onCreatePlace || null}
                />
                { byGroup &&
                    <span className="messageLinker__ofGroup">
                        <FormattedMessage id="app.messages.ofGroup" defaultMessage="(of the group)" />
                    </span>
                }
                { !place && ofGroup.length > 1 && ofGroup.map((item) =>
                    <button key={item.id} type="button" className="pill pill--outline messageLinker__shortcut" disabled={busy} onClick={() => setPlace(item)}>
                        {item.name}
                        <span className="messageLinker__ofGroup">
                            <FormattedMessage id="app.messages.ofGroup" defaultMessage="(of the group)" />
                        </span>
                    </button>
                )}
                <sl-dropdown ref={dropdown} placement="bottom-start" hoist>
                    <button slot="trigger" type="button" className="pill pill--outline pill--caret" disabled={!chosen || busy}>
                        <FormattedMessage id="app.messages.chooseStatus" defaultMessage="Choose status" />
                    </button>
                    <div className="popoverPanel messagePicker__panel">
                        <KeyValues keys={keys} onPick={pick} />
                    </div>
                </sl-dropdown>
            </div>
            { outcome &&
                <LinkOutcome outcome={outcome} place={outcome.place} onUndo={onUndo && undo} onReload={onReload} />
            }
        </div>
    );
}
