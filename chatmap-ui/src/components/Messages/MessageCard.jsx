import { useId } from "react";
import { FormattedMessage, FormattedNumber, useIntl } from "react-intl";

import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";
import SlIconButton from "@shoelace-style/shoelace/dist/react/icon-button/index.js";
import SlTooltip from "@shoelace-style/shoelace/dist/react/tooltip/index.js";

import TimeAgo from "../TimeAgo";
import { onlyLocation } from "./linkStates.js";
import { coordsOf, highlighted, senderOf } from "./messages.js";
import "./linkStates.css";
import { MarkedFirst } from "./ReviewOrder.jsx";

// "350 m", "1.2 km"
export function Distance({ meters }) {
    return meters < 1000 ?
        <FormattedNumber value={meters} style="unit" unit="meter" maximumFractionDigits={0} /> :
        <FormattedNumber value={meters / 1000} style="unit" unit="kilometer" maximumFractionDigits={1} />;
}

/**
 * Where a message was sent from: a shared location, with the place of the
 * map nearest to it, and its coordinates to copy; or what it says when they
 * cannot be read. A message that is only a location says so.
 *
 * @param {object} near The nearest place, { name, meters }, or null
 * @param {boolean} alone Whether the message says nothing else
 */
function MessageLocation({ location, near, alone }) {
    const intl = useIntl();
    const coords = coordsOf(location);

    return (
        <p className="messageCard__location">
            <SlIcon name="geo-alt" />
            { coords ?
                <span>
                    { alone ?
                        near ?
                            <FormattedMessage
                                id="app.messages.onlyLocationNear"
                                defaultMessage="A location, without text, {distance} from {place}"
                                values={{ distance: <Distance meters={near.meters} />, place: <strong>{near.name}</strong> }}
                            /> :
                            <FormattedMessage id="app.messages.onlyLocation" defaultMessage="A location, without text" />
                    : near ?
                        <FormattedMessage
                            id="app.messages.locationNear"
                            defaultMessage="Location shared, {distance} from {place}"
                            values={{ distance: <Distance meters={near.meters} />, place: <strong>{near.name}</strong> }}
                        /> :
                        <FormattedMessage id="app.messages.locationShared" defaultMessage="Location shared" />
                    }
                    <span className="messageCard__coords">{coords.join(", ")}</span>
                </span> :
                <span>{location}</span>
            }
            { coords &&
                <SlIconButton
                    name="copy"
                    label={intl.formatMessage({ id: "app.messages.copyLocation", defaultMessage: "Copy the coordinates" })}
                    onClick={() => navigator.clipboard?.writeText(coords.join(","))}
                />
            }
        </p>
    );
}

/**
 * The ✕ of a message linked to a place: it cannot be dismissed until its
 * links are undone, and it says so when pointed at or reached with the keyboard.
 */
function DismissBlocked() {
    const intl = useIntl();
    const why = useId();
    const reason = intl.formatMessage({
        id: "app.messages.dismissLinked",
        defaultMessage: "It is linked to a place. Undo its links to dismiss it.",
    });

    return (
        <SlTooltip content={reason} className="messageCard__dismiss">
            <button
                type="button"
                className="messageCard__dismissBlocked"
                aria-disabled="true"
                aria-label={intl.formatMessage({ id: "app.messages.dismiss", defaultMessage: "Dismiss: it says nothing about the places" })}
                aria-describedby={why}
            >
                <SlIcon name="x-lg" />
            </button>
            <span id={why} className="linkStates__hidden">{reason}</span>
        </SlTooltip>
    );
}

/**
 * A message of a group. On top, who sent it (as a pseudonym), how long ago,
 * and in which group when the page shows them all; then what it says, whole,
 * as a bubble (with what a rule looked for marked), and where it was sent
 * from; below, what it suggests and what can be done with it.
 *
 * @param {string} groupName The name of its group; none when the page shows one group
 * @param {object} near The place nearest to where it was sent from, if it says (see nearestPlace)
 * @param {node} children What can be done with it
 * @param {function} onDismiss Dismisses it, from the ✕ at the top right; without it there is no ✕
 * @param {boolean} linked Whether it is linked to a place: without onDismiss, the ✕ shows disabled, saying why
 * @param {number} markedLine A line to mark, the one a suggestion pointed at comes from; null for none
 */
export default function MessageCard({ message, groupName, near, onDismiss, linked, markedLine = null, children }) {
    const intl = useIntl();
    const sender = senderOf(message.sender);

    return (
        <article className="messageCard">
            <header className="messageCard__header">
                <span className="messageCard__sender" style={{ "--sender-hue": sender.hue }}>
                    <span className="messageCard__avatar" aria-hidden="true" />
                    <FormattedMessage id="app.messages.person" defaultMessage="Person {code}" values={{ code: sender.code }} />
                </span>
                <span className="messageCard__when">
                    <time dateTime={message.sent_at} title={new Date(message.sent_at).toLocaleString()}>
                        <TimeAgo datetime={message.sent_at} />
                    </time>
                    { groupName &&
                        <FormattedMessage id="app.messages.inGroup" defaultMessage="in {group}" values={{ group: <strong>{groupName}</strong> }} />
                    }
                </span>
                <MarkedFirst message={message} />
                { onDismiss ?
                    <SlIconButton
                        className="messageCard__dismiss"
                        name="x-lg"
                        label={intl.formatMessage({ id: "app.messages.dismiss", defaultMessage: "Dismiss: it says nothing about the places" })}
                        onClick={onDismiss}
                    /> :
                    linked && <DismissBlocked />
                }
            </header>
            { message.text &&
                <p className="messageCard__text">
                    {/* Each line in its own direction: an Arabic line does not turn around the others */}
                    { message.text.split("\n").map((line, number) =>
                        <span key={number} className={`messageCard__line ${number === markedLine ? "messageCard__line--marked" : ""}`} dir="auto">
                            { highlighted(line, message.highlights || []).map((piece, index) => piece.match ?
                                <mark key={index} className="messageCard__mark">{piece.text}</mark> : piece.text
                            )}
                        </span>
                    )}
                </p>
            }
            { message.location && <MessageLocation location={message.location} near={near} alone={onlyLocation(message)} /> }
            <div className="messageCard__actions">{children}</div>
        </article>
    );
}
