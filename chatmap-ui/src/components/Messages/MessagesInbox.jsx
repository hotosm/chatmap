import { useMemo } from "react";
import { FormattedMessage } from "react-intl";

import SlSpinner from "@shoelace-style/shoelace/dist/react/spinner/index.js";

import { linkableKeys } from "../Tags";
import GroupsPicker from "./GroupsPicker.jsx";
import MessageCard from "./MessageCard.jsx";
import MessageLinker from "./MessageLinker.jsx";
import MessageLinks from "./MessageLinks.jsx";
import { liveLinks } from "./messages.js";
import useGroupName from "./useGroupName.js";
import useMessageActions from "./useMessageActions.js";
import useMessages from "./useMessages.js";

// The messages to read: all the ones not dismissed, or only some
const STATES = [
    { state: null, label: <FormattedMessage id="app.messages.stateAll" defaultMessage="All" /> },
    { state: "new", label: <FormattedMessage id="app.messages.stateNew" defaultMessage="Not reviewed" /> },
    { state: "linked", label: <FormattedMessage id="app.messages.stateLinked" defaultMessage="Linked" /> },
    { state: "dismissed", label: <FormattedMessage id="app.messages.stateDismissed" defaultMessage="Dismissed" /> },
];

// A message dismissed right now, in its place, to bring it back
function Dismissed({ message, onBack }) {
    return (
        <p className="messagesInbox__dismissed">
            <FormattedMessage id="app.messages.dismissed" defaultMessage="Dismissed" />
            <button type="button" className="messageLinks__undo" onClick={() => onBack(message)}>
                <FormattedMessage id="app.messages.undo" defaultMessage="Undo" />
            </button>
        </p>
    );
}

/**
 * The messages of the groups a map listens to: the groups at the left, to
 * read all of them or one (and, for a live map, to choose them), and their
 * messages at the right, newest first. Each one is linked to places of the
 * map and their status, or dismissed.
 *
 * @param {object} mapData The map, with its points and keys
 */
export default function MessagesInbox({ mapData }) {
    const mapId = mapData.id;
    const {
        phone, changed, groups, names, groupId, setGroupId, state, setState,
        messages, more, loading, error, loadMore, replace,
    } = useMessages(mapId);
    const { link, undoLink, dismiss } = useMessageActions(replace);
    const keys = useMemo(() => linkableKeys(mapData.keys), [mapData.keys]);
    const enabled = (groups || []).filter((group) => group.enabled);
    const groupName = useGroupName();
    const nameOf = (id) => groupName(names[id]);

    const choice = (id, name, chosen, choose) =>
        <li key={id || "all"}>
            <button
                type="button"
                className="messagesInbox__group"
                aria-current={chosen === id ? "true" : undefined}
                onClick={() => choose(id)}
            >
                {name}
            </button>
        </li>;
    const group = (id, name) => choice(id, name, groupId, setGroupId);

    const card = (message) => {
        // Dismissed here, it waits in its place to be brought back
        if (message.dismissed_at && state !== "dismissed") {
            return <Dismissed key={message.id} message={message} onBack={(item) => dismiss(item, false)} />;
        }
        // A linked message is not dismissed: its links are undone first
        const dismissable = !message.dismissed_at && liveLinks(message).length === 0;
        return (
            <MessageCard
                key={message.id}
                message={message}
                groupName={nameOf(message.group_id)}
                onDismiss={dismissable ? () => dismiss(message, true) : null}
            >
                <MessageLinks message={message} mapData={mapData} onUndo={undoLink} />
                { message.dismissed_at ?
                    <button type="button" className="pill pill--outline" onClick={() => dismiss(message, false)}>
                        <FormattedMessage id="app.messages.bringBack" defaultMessage="Bring back" />
                    </button> :
                    <MessageLinker message={message} mapData={mapData} keys={keys} onLink={link} />
                }
            </MessageCard>
        );
    };

    return (
        <div className="messagesInbox">
            <nav className="messagesInbox__groups">
                <div className="messagesInbox__groupsList">
                    <ul>
                        { group(null, <FormattedMessage id="app.messages.allGroups" defaultMessage="All groups" />) }
                        { enabled.map((item) => group(item.id, nameOf(item.id))) }
                    </ul>
                    { mapData.is_live && phone && <GroupsPicker mapId={mapId} phone={phone} onChange={changed} /> }
                    <ul className="messagesInbox__states">
                        { STATES.map((item) => choice(item.state, item.label, state, setState)) }
                    </ul>
                </div>
            </nav>

            <section className="messagesInbox__messages" aria-busy={loading}>
                { messages.map(card) }

                { !loading && !error && messages.length === 0 && groups &&
                    <p className="messagesInbox__empty">
                        { enabled.length === 0 ?
                            <FormattedMessage
                                id="app.messages.noGroups"
                                defaultMessage="Choose the groups this map listens to, and their messages will show here."
                            /> :
                            state ?
                                <FormattedMessage id="app.messages.noneHere" defaultMessage="There are no messages here." /> :
                                <FormattedMessage id="app.messages.none" defaultMessage="There are no messages yet." />
                        }
                    </p>
                }
                { error &&
                    <p className="messagesInbox__error" role="alert">
                        <FormattedMessage id="app.messages.notRead" defaultMessage="The messages could not be read. Try again." />
                    </p>
                }
                { loading && <SlSpinner className="messagesInbox__loading" /> }
                { more && !loading &&
                    <button type="button" className="pill pill--outline messagesInbox__more" onClick={loadMore}>
                        <FormattedMessage id="app.messages.more" defaultMessage="Older messages" />
                    </button>
                }
            </section>
        </div>
    );
}
