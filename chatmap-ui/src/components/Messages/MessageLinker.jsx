import { useMemo, useRef, useState } from "react";
import { FormattedMessage } from "react-intl";

import { KeyValues, isExpired } from "../Tags";
import PlacePicker from "./PlacePicker.jsx";
import { coordsOf, liveLinks, placesOf } from "./messages.js";

// Why a link did not change what the place shows now, or was not made
const OLDER = "older";
const EXPIRED = "expired";
const TWICE = "twice";

// Why the API did not take a link, by its status
const NOT_TAKEN = {
    404: <FormattedMessage id="app.messages.linkGone" defaultMessage="That place or this message is no longer there. Reload the page." />,
    409: <FormattedMessage
        id="app.messages.linkConflict"
        defaultMessage="It is already linked that way, or the message was dismissed. Reload the page."
    />,
};
const NOT_LINKED = <FormattedMessage id="app.messages.notLinked" defaultMessage="It could not be linked. Try again." />;

/**
 * Links a message to a place of the map: "Choose place", then "Choose
 * status" with the values of its keys. Picking a value gives it to the
 * place at the time of the message, and says when that does not change
 * what the place shows: it had something newer, or the value already expired.
 *
 * @param {object} mapData The map, with its points (features) and keys
 * @param {function} onLink Gets the message and the change; answers { status, answer } (see useMessageActions)
 */
export default function MessageLinker({ message, mapData, keys, onLink }) {
    const dropdown = useRef();
    const [place, setPlace] = useState(null);
    const [busy, setBusy] = useState(false);
    // The status of a link the API did not take, or null
    const [failed, setFailed] = useState(null);
    const [notice, setNotice] = useState(null);
    const places = useMemo(
        () => placesOf(mapData.features, coordsOf(message.location)), [mapData.features, message.location],
    );

    const pick = async (keyId, change) => {
        setNotice(null);
        setFailed(null);
        // The same message giving the same value to the same place says nothing new
        const twice = liveLinks(message).some((link) =>
            link.point_id === place.id && link.key_id === keyId &&
            (change.value_id ? link.value_id === change.value_id : link.value === change.value)
        );
        if (twice) {
            dropdown.current && dropdown.current.hide();
            setNotice(TWICE);
            return;
        }
        setBusy(true);
        const { status, answer } = await onLink(message, { point_id: place.id, key_id: keyId, ...change });
        setBusy(false);
        if (!answer) {
            setFailed(status);
            return;
        }
        dropdown.current && dropdown.current.hide();
        const key = keys.find((item) => item.key.id === keyId).key;
        const value = (key.values || []).find((item) => item.id === change.value_id);
        if (!answer.applied) setNotice(OLDER);
        else if (value && isExpired(value, { confirmed_at: message.sent_at })) setNotice(EXPIRED);
        setPlace(null);
    };

    return (
        <div className="messageLinker">
            <div className="messageLinker__pickers">
                <PlacePicker places={places} place={place} onPick={setPlace} disabled={busy} />
                <sl-dropdown ref={dropdown} placement="bottom-start" hoist>
                    <button slot="trigger" type="button" className="pill pill--outline pill--caret" disabled={!place || busy}>
                        <FormattedMessage id="app.messages.chooseStatus" defaultMessage="Choose status" />
                    </button>
                    <div className="popoverPanel messagePicker__panel">
                        <KeyValues keys={keys} onPick={pick} />
                    </div>
                </sl-dropdown>
            </div>
            { failed !== null &&
                <p className="messageLinker__notice messageLinker__notice--error" role="alert">
                    {NOT_TAKEN[failed] || NOT_LINKED}
                </p>
            }
            { notice === OLDER &&
                <p className="messageLinker__notice" role="status">
                    <FormattedMessage
                        id="app.messages.linkedOlder"
                        defaultMessage="It went to the history of the place: it has something newer, which it keeps showing."
                    />
                </p>
            }
            { notice === TWICE &&
                <p className="messageLinker__notice" role="status">
                    <FormattedMessage
                        id="app.messages.linkedTwice"
                        defaultMessage="This message already gives that value to that place."
                    />
                </p>
            }
            { notice === EXPIRED &&
                <p className="messageLinker__notice" role="status">
                    <FormattedMessage
                        id="app.messages.linkedExpired"
                        defaultMessage="The message is older than that value lasts: the place shows it as unknown."
                    />
                </p>
            }
        </div>
    );
}
