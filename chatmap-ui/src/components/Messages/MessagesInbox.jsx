import { FormattedMessage } from "react-intl";

import SlSpinner from "@shoelace-style/shoelace/dist/react/spinner/index.js";

import GroupsPicker from "./GroupsPicker.jsx";
import MessageCard from "./MessageCard.jsx";
import useGroupName from "./useGroupName.js";
import useMessages from "./useMessages.js";

/**
 * The messages of the groups a map listens to: the groups at the left, to
 * read all of them or one (and, for a live map, to choose them), and their
 * messages at the right, newest first.
 *
 * @param {boolean} live Whether the map is live: only then its groups can be chosen
 */
export default function MessagesInbox({ mapId, live }) {
    const {
        phone, changed, groups, names, groupId, setGroupId, messages, more, loading, error, loadMore,
    } = useMessages(mapId);
    const enabled = (groups || []).filter((group) => group.enabled);
    const groupName = useGroupName();
    const nameOf = (id) => groupName(names[id]);

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

    return (
        <div className="messagesInbox">
            <nav className="messagesInbox__groups">
                <div className="messagesInbox__groupsList">
                    <ul>
                        { group(null, <FormattedMessage id="app.messages.allGroups" defaultMessage="All groups" />) }
                        { enabled.map((item) => group(item.id, nameOf(item.id))) }
                    </ul>
                    { live && phone && <GroupsPicker mapId={mapId} phone={phone} onChange={changed} /> }
                </div>
            </nav>

            <section className="messagesInbox__messages" aria-busy={loading}>
                { messages.map((message) =>
                    <MessageCard key={message.id} message={message} groupName={nameOf(message.group_id)} />
                )}

                { !loading && !error && messages.length === 0 && groups &&
                    <p className="messagesInbox__empty">
                        { enabled.length === 0 ?
                            <FormattedMessage
                                id="app.messages.noGroups"
                                defaultMessage="Choose the groups this map listens to, and their messages will show here."
                            /> :
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
