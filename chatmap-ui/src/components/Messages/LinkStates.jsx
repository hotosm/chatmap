import { useEffect, useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";

import TimeAgo from "../TimeAgo";
import { EXPIRED, FAILED, OLDER, TWICE } from "./linkStates.js";
import "./linkStates.css";

// The icon of each outcome of a link
const ICONS = { [OLDER]: "clock-history", [EXPIRED]: "clock", [TWICE]: "info-circle", [FAILED]: "exclamation-triangle" };

// How long a message stays dismissed before the notice to undo it goes away
const TOAST_FOR = 8000;

// "24 hours", "2 days": a time to say, as linkStates counts it
function Duration({ value, unit }) {
    const intl = useIntl();
    return intl.formatNumber(value, { style: "unit", unit, unitDisplay: "long" });
}

// Why the API did not take a link, by its status, and whether reading the messages again helps
function NotTaken({ status, place }) {
    if (status === 404) {
        return <FormattedMessage
            id="app.messages.linkGone"
            defaultMessage="It could not be linked: {place} was deleted, or this message is no longer kept."
            values={{ place: <strong>{place}</strong> }}
        />;
    }
    if (status === 409) {
        return <FormattedMessage
            id="app.messages.linkConflict"
            defaultMessage="It could not be linked: it is already linked that way, or the message was dismissed."
        />;
    }
    return <FormattedMessage id="app.messages.notLinked" defaultMessage="It could not be linked. Try again." />;
}

// What a link did, in words with its place, its values and their times
function OutcomeText({ outcome, place }) {
    const name = <strong>{place}</strong>;
    switch (outcome.kind) {
    case OLDER:
        return outcome.shown ?
            <FormattedMessage
                id="app.messages.linkedOlder"
                defaultMessage="Saved in the history of {place}. It has a newer report ({value}, {ago}), so the map keeps showing {value}."
                values={{ place: name, value: <strong>{outcome.shown.value}</strong>, ago: <TimeAgo datetime={outcome.shownAt} /> }}
            /> :
            <FormattedMessage
                id="app.messages.linkedOlderUnknown"
                defaultMessage="Saved in the history of {place}: it has a newer report, which the map keeps showing."
                values={{ place: <bdi>{name}</bdi> }}
            />;
    case EXPIRED:
        return <FormattedMessage
            id="app.messages.linkedExpired"
            defaultMessage="{value} lasts {lasts} and this message is {age} old: {place} shows as unknown on the map."
            values={{
                value: <strong>{outcome.value.value}</strong>,
                lasts: <Duration {...outcome.lasts} />,
                age: <Duration {...outcome.age} />,
                place: name,
            }}
        />;
    case TWICE:
        return <FormattedMessage
            id="app.messages.linkedTwice"
            defaultMessage="This message already gives {value} to {place}. Nothing changed."
            values={{ value: <strong>{outcome.value}</strong>, place: name }}
        />;
    default:
        return <NotTaken status={outcome.status} place={place} />;
    }
}

/**
 * What a link did when it did not change what the place shows, or was not
 * made, as a bar inside the card: an icon, what happened with the place and
 * its values, and what can be done. A link that went to the history or
 * whose value already expired can be undone; one that was not made can be
 * read again, when the messages shown are no longer as they are.
 *
 * @param {object} outcome { kind, ... } (see linkOutcome); a failed one has the status of the API
 * @param {string} place The name of the place
 * @param {function} onUndo Undoes the link; answers null when it is not undone
 * @param {function} onReload Reads the messages again
 */
export function LinkOutcome({ outcome, place, onUndo, onReload }) {
    const [busy, setBusy] = useState(false);
    const [notUndone, setNotUndone] = useState(false);
    const failed = outcome.kind === FAILED;
    const undoable = (outcome.kind === OLDER || outcome.kind === EXPIRED) && onUndo;
    const reloadable = failed && [404, 409].includes(outcome.status) && onReload;

    const undo = async () => {
        setBusy(true);
        const undone = await onUndo(outcome.link);
        setBusy(false);
        setNotUndone(!undone);
    };

    return (
        <div className={`linkOutcome linkOutcome--${outcome.kind}`} role={failed ? "alert" : "status"}>
            <SlIcon className="linkOutcome__icon" name={ICONS[outcome.kind]} />
            <p className="linkOutcome__text">
                <OutcomeText outcome={outcome} place={place} />
                { notUndone &&
                    <span className="linkOutcome__error">
                        {" "}<FormattedMessage id="app.messages.notUndone" defaultMessage="It could not be undone. Try again." />
                    </span>
                }
            </p>
            { undoable &&
                <button type="button" className="linkOutcome__action" disabled={busy} onClick={undo}>
                    <SlIcon name="arrow-counterclockwise" />
                    <FormattedMessage id="app.messages.undoLink" defaultMessage="Undo link" />
                </button>
            }
            { reloadable &&
                <button type="button" className="linkOutcome__action" onClick={onReload}>
                    <SlIcon name="arrow-clockwise" />
                    <FormattedMessage id="app.messages.reload" defaultMessage="Reload" />
                </button>
            }
        </div>
    );
}

/**
 * A notice at the bottom of the page after dismissing a message, to undo
 * it; it goes away after a few seconds, or when another message is dismissed.
 *
 * @param {object} message The message dismissed
 * @param {function} onUndo Brings it back
 * @param {function} onClose The notice goes away
 */
export function DismissedToast({ message, onUndo, onClose }) {
    useEffect(() => {
        const timer = setTimeout(onClose, TOAST_FOR);
        return () => clearTimeout(timer);
    }, [message, onClose]);

    return (
        <div className="dismissedToast" role="status">
            <FormattedMessage id="app.messages.dismissedToast" defaultMessage="Message dismissed" />
            <button type="button" className="dismissedToast__undo" onClick={() => { onUndo(message); onClose(); }}>
                <SlIcon name="arrow-counterclockwise" />
                <FormattedMessage id="app.messages.undo" defaultMessage="Undo" />
            </button>
        </div>
    );
}

/**
 * Under the last message, when there are no older ones: how long the map
 * keeps them, so it is clear the older ones were removed and not lost.
 *
 * @param {number} days The days the map keeps the messages of its groups
 * @param {boolean} oneGroup Whether the messages of one group are read
 */
export function KeptNote({ days, oneGroup }) {
    return (
        <p className="keptNote">
            { oneGroup ?
                <FormattedMessage
                    id="app.messages.keptInGroup"
                    defaultMessage="Kept for {days, plural, one {# day} other {# days}} in this group: older ones were removed."
                    values={{ days }}
                /> :
                <FormattedMessage
                    id="app.messages.keptInGroups"
                    defaultMessage="Kept for {days, plural, one {# day} other {# days}} in these groups: older ones were removed."
                    values={{ days }}
                />
            }
        </p>
    );
}
