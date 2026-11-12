import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlSpinner from "@shoelace-style/shoelace/dist/react/spinner/index.js";

import { linkableKeys } from "../Tags";
import GroupsPicker from "./GroupsPicker.jsx";
import InboxCard from "./InboxCard.jsx";
import { DismissedToast, KeptNote } from "./LinkStates.jsx";
import { dayOf, groupPointsOf, placesOf } from "./messages.js";
import { startsBeforeReviewed } from "./order.js";
import { BeforeReviewed } from "./ReviewOrder.jsx";
import useAddedPlaces from "./useAddedPlaces.js";
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

// What each tab says when it has no messages
const EMPTY = {
    new: <FormattedMessage id="app.messages.noneNew" defaultMessage="Every message was reviewed: linked or dismissed." />,
    linked: <FormattedMessage id="app.messages.noneLinkedTab" defaultMessage="No message was linked to a place yet." />,
    dismissed: <FormattedMessage id="app.messages.noneDismissed" defaultMessage="No message was dismissed." />,
};

// The day of the messages under it: "Today", "Yesterday", or its date
function Day({ sentAt }) {
    const intl = useIntl();
    const day = new Date(sentAt);
    const daysAgo = Math.round((new Date(dayOf(new Date())) - new Date(dayOf(day))) / 86400000);
    const name = daysAgo === 0 ? intl.formatMessage({ id: "app.messages.today", defaultMessage: "Today" }) :
        daysAgo === 1 ? intl.formatMessage({ id: "app.messages.yesterday", defaultMessage: "Yesterday" }) :
        intl.formatDate(day, { weekday: "long", day: "numeric", month: "long" });
    return <h3 className="messagesInbox__day">{name}</h3>;
}

// The way to the older messages: they are read as it comes into sight, or with a click
function OlderMessages({ onReach }) {
    const button = useRef();
    useEffect(() => {
        const observer = new IntersectionObserver((entries) => entries.some((entry) => entry.isIntersecting) && onReach());
        observer.observe(button.current);
        return () => observer.disconnect();
    }, [onReach]);

    return (
        <button ref={button} type="button" className="pill pill--outline messagesInbox__more" onClick={onReach}>
            <FormattedMessage id="app.messages.more" defaultMessage="Load older messages" />
        </button>
    );
}

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
export default function MessagesInbox({ mapData: read }) {
    // With the places added from the messages while the page is open
    const [mapData, addPlace] = useAddedPlaces(read);
    const mapId = mapData.id;
    const {
        phone, changed, groups, names, groupId, setGroupId, state, setState,
        messages, more, loading, error, loadMore, reload, replace, readNewer,
    } = useMessages(mapId);
    const { link, undoLink, dismiss } = useMessageActions(replace);
    const keys = useMemo(() => linkableKeys(mapData.keys), [mapData.keys]);
    const places = useMemo(() => placesOf(mapData.features, null), [mapData.features]);
    const groupPoints = useMemo(() => groupPointsOf(groups), [groups]);
    const actions = { link, undoLink, dismiss, onReload: reload, onCreatePlace: addPlace };
    const enabled = (groups || []).filter((group) => group.enabled);
    const groupName = useGroupName();
    const nameOf = (id) => groupName(names[id]);

    // The message just dismissed, with a notice to undo it
    const [dismissedNow, setDismissedNow] = useState(null);
    const closeToast = useCallback(() => setDismissedNow(null), []);

    const group = (id, name) =>
        <li key={id || "all"}>
            <button
                type="button"
                className="messagesInbox__group"
                aria-current={groupId === id ? "true" : undefined}
                onClick={() => setGroupId(id)}
            >
                {name}
            </button>
        </li>;

    const card = (message) => {
        // Dismissed here, it waits in its place to be brought back
        if (message.dismissed_at && state !== "dismissed") {
            return <Dismissed key={message.id} message={message} onBack={(item) => dismiss(item, false)} />;
        }
        return (
            <InboxCard
                key={message.id}
                message={message}
                mapData={mapData}
                keys={keys}
                groupName={groupId ? null : nameOf(message.group_id)}
                groupPointIds={groupPoints[message.group_id]}
                actions={actions}
                onDismiss={async () => setDismissedNow(await dismiss(message, true))}
            />
        );
    };

    // Back at the top of the list, the newest are read again: what just arrived shows
    const backAtTop = (event) => event.currentTarget.scrollTop === 0 && readNewer();

    // The messages to read, as tabs over them
    const tab = (item) =>
        <button
            key={item.state || "all"}
            type="button"
            role="tab"
            className="messagesInbox__tab"
            aria-selected={state === item.state}
            onClick={() => setState(item.state)}
        >
            {item.label}
        </button>;

    return (
        <div className="messagesInbox">
            <nav className="messagesInbox__groups">
                <div className="messagesInbox__groupsList">
                    <ul>
                        { group(null, <FormattedMessage id="app.messages.allGroups" defaultMessage="All groups" />) }
                        { enabled.map((item) => group(item.id, nameOf(item.id))) }
                    </ul>
                    { mapData.is_live && phone && <GroupsPicker mapId={mapId} phone={phone} places={places} onChange={changed} /> }
                </div>
            </nav>

            <div className="messagesInbox__main">
                <div className="messagesInbox__toolbar">
                    <div className="messagesInbox__tabs" role="tablist">{ STATES.map(tab) }</div>
                </div>

                <section className="messagesInbox__messages" aria-busy={loading} onScroll={backAtTop}>
                    { messages.map((message, index) =>
                        <Fragment key={message.id}>
                            { startsBeforeReviewed(messages, index) && <BeforeReviewed /> }
                            { (index === 0 || startsBeforeReviewed(messages, index) ||
                                dayOf(messages[index - 1].sent_at) !== dayOf(message.sent_at)) &&
                                <Day sentAt={message.sent_at} />
                            }
                            {card(message)}
                        </Fragment>
                    )}

                    { !loading && !error && messages.length === 0 && groups &&
                        <p className="messagesInbox__empty">
                            { enabled.length === 0 ?
                                <FormattedMessage
                                    id="app.messages.noGroups"
                                    defaultMessage="Choose the groups this map listens to, and their messages will show here."
                                /> :
                                state ?
                                    EMPTY[state] :
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
                        <OlderMessages onReach={loadMore} />
                    }
                    { !more && !loading && !error && messages.length > 0 && phone && phone.kept_days > 0 &&
                        <KeptNote days={phone.kept_days} oneGroup={Boolean(groupId)} />
                    }
                </section>
            </div>
            { dismissedNow &&
                <DismissedToast message={dismissedNow} onUndo={(item) => dismiss(item, false)} onClose={closeToast} />
            }
        </div>
    );
}
