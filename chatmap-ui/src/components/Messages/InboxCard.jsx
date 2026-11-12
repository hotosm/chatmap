import { useState } from "react";
import { FormattedMessage } from "react-intl";

import MessageCard from "./MessageCard.jsx";
import MessageLines from "./MessageLines.jsx";
import MessageLinker from "./MessageLinker.jsx";
import MessageLinks from "./MessageLinks.jsx";
import { coordsOf, linkOf, liveLinks, nearestPlace } from "./messages.js";

// Who dismissed a message: a person, or a rule that hides
export function DismissedBy({ message }) {
    return message.dismissed_by_rule ?
        <FormattedMessage id="app.messages.dismissedByRule" defaultMessage="Dismissed by a rule" /> :
        <FormattedMessage id="app.messages.dismissed" defaultMessage="Dismissed" />;
}

/**
 * A message of the inbox, to review: its card with what it suggests as rows
 * (when it suggests something), the links it made, and the pickers to link
 * it by hand. A suggestion that lacks its place or its value is completed
 * with the pickers, starting from its place when it has one.
 *
 * @param {object} actions What can be done with it (see useMessageActions) and onReload, onCreatePlace
 * @param {array} groupPointIds The places its group always speaks of, if its owner said so
 */
export default function InboxCard({ message, mapData, keys, groupName, groupPointIds, actions, onDismiss }) {
    // The place of the suggestion being completed with the pickers
    const [preset, setPreset] = useState(null);
    const { link, undoLink, dismiss, answerLine, renew, onReload, onCreatePlace } = actions;
    // A linked message is not dismissed: its links are undone first
    const linked = liveLinks(message).length > 0;
    const dismissable = !message.dismissed_at && !linked;
    const suggests = (message.suggestions || []).length > 0 && !message.dismissed_at;
    // The links its rows show, with what it suggested, are not listed again under them
    const shown = suggests ? (message.suggestions || [])
        .filter((item) => item.state === "accepted").map((item) => linkOf(message, item)).filter(Boolean)
        .map((link) => link.change_id) : [];

    return (
        <MessageCard
            message={message}
            groupName={groupName}
            near={nearestPlace(mapData.features, coordsOf(message.location))}
            onDismiss={dismissable ? onDismiss : null}
            linked={linked && !message.dismissed_at}
            lines={suggests &&
                <MessageLines
                    message={message}
                    mapData={mapData}
                    onConfirm={link}
                    onAnswer={answerLine}
                    onRenew={renew}
                    onChoose={(suggestion) => setPreset(suggestion.point_id)}
                    onUndo={undoLink}
                />
            }
        >
            <MessageLinks message={message} mapData={mapData} onUndo={undoLink} shown={shown} />
            { message.dismissed_at ?
                <div className="messageCard__dismissedBy">
                    <span className="pointMessages__muted"><DismissedBy message={message} /></span>
                    <button type="button" className="pill pill--outline" onClick={() => dismiss(message, false)}>
                        <FormattedMessage id="app.messages.bringBack" defaultMessage="Bring back" />
                    </button>
                </div> :
                <MessageLinker
                    key={preset || "none"}
                    message={message}
                    mapData={mapData}
                    keys={keys}
                    onLink={link}
                    onUndo={undoLink}
                    onReload={onReload}
                    onCreatePlace={onCreatePlace}
                    groupPointIds={groupPointIds}
                    presetPointId={preset}
                />
            }
        </MessageCard>
    );
}
