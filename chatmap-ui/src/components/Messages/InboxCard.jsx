import { FormattedMessage } from "react-intl";

import MessageCard from "./MessageCard.jsx";
import MessageLinker from "./MessageLinker.jsx";
import MessageLinks from "./MessageLinks.jsx";
import { coordsOf, liveLinks, nearestPlace } from "./messages.js";

/**
 * A message of the inbox, to review: its card with the links it made, and
 * the pickers to link it.
 *
 * @param {object} actions What can be done with it (see useMessageActions) and onReload, onCreatePlace
 * @param {array} groupPointIds The places its group always speaks of, if its owner said so
 */
export default function InboxCard({ message, mapData, keys, groupName, groupPointIds, actions, onDismiss }) {
    const { link, undoLink, dismiss, onReload, onCreatePlace } = actions;
    // A linked message is not dismissed: its links are undone first
    const linked = liveLinks(message).length > 0;
    const dismissable = !message.dismissed_at && !linked;

    return (
        <MessageCard
            message={message}
            groupName={groupName}
            near={nearestPlace(mapData.features, coordsOf(message.location))}
            onDismiss={dismissable ? onDismiss : null}
            linked={linked && !message.dismissed_at}
        >
            <MessageLinks message={message} mapData={mapData} onUndo={undoLink} />
            { message.dismissed_at ?
                <div className="messageCard__dismissedBy">
                    <span className="pointMessages__muted">
                        <FormattedMessage id="app.messages.dismissed" defaultMessage="Dismissed" />
                    </span>
                    <button type="button" className="pill pill--outline" onClick={() => dismiss(message, false)}>
                        <FormattedMessage id="app.messages.bringBack" defaultMessage="Bring back" />
                    </button>
                </div> :
                <MessageLinker
                    message={message}
                    mapData={mapData}
                    keys={keys}
                    onLink={link}
                    onUndo={undoLink}
                    onReload={onReload}
                    onCreatePlace={onCreatePlace}
                    groupPointIds={groupPointIds}
                />
            }
        </MessageCard>
    );
}
