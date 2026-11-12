import { FormattedMessage, useIntl } from "react-intl";

import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";
import SlIconButton from "@shoelace-style/shoelace/dist/react/icon-button/index.js";

import TimeAgo from "../TimeAgo";
import { coordsOf } from "./messages.js";

// Where a message was sent from: its coordinates, to copy, or what it says when they cannot be read
function MessageLocation({ location }) {
    const intl = useIntl();
    const coords = coordsOf(location);
    const text = coords ? coords.join(", ") : location;

    return (
        <p className="messageCard__location">
            <SlIcon name="geo-alt" />
            <span>{text}</span>
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
 * A message of a group: what it says and where it was sent from (if it says),
 * with how long ago and in which group below.
 *
 * @param {node} children What can be done with it, at the bottom left
 * @param {function} onDismiss Dismisses it, from the ✕ at the top right; without it there is no ✕
 */
export default function MessageCard({ message, groupName, onDismiss, children }) {
    const intl = useIntl();

    return (
        <article className="messageCard">
            { onDismiss &&
                <SlIconButton
                    className="messageCard__dismiss"
                    name="x-lg"
                    label={intl.formatMessage({ id: "app.messages.dismiss", defaultMessage: "Dismiss: it says nothing about the places" })}
                    onClick={onDismiss}
                />
            }
            { message.text && <p className="messageCard__text">{message.text}</p> }
            { message.location && <MessageLocation location={message.location} /> }
            <footer className="messageCard__footer">
                <div className="messageCard__actions">{children}</div>
                <span className="messageCard__meta">
                    <FormattedMessage
                        id="app.messages.agoIn"
                        defaultMessage="{ago} in {group}"
                        values={{
                            ago: <time dateTime={message.sent_at} title={new Date(message.sent_at).toLocaleString()}>
                                <TimeAgo datetime={message.sent_at} />
                            </time>,
                            group: <strong>{groupName}</strong>,
                        }}
                    />
                </span>
            </footer>
        </article>
    );
}
