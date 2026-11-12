import { useCallback } from "react";

import useMessagesApi from "./useMessagesApi.js";

/**
 * What the owner of a map does with a message: link it to a point, undo a
 * link, dismiss it or bring it back. Each one gives the message as it is
 * after it to `replace`, and answers null when the API does not take it
 * (link answers the status too, to tell why).
 *
 * @param {function} replace Gets a message after a change
 */
export default function useMessageActions(replace) {
    const { linkMessage, setLinkUndone, setDismissed } = useMessagesApi();

    // { status, answer }; answer is { link, tags, applied }, and applied is false when the point had something newer
    const link = useCallback(async (message, change) => {
        const result = await linkMessage(message.id, change);
        if (result.answer) replace({ ...message, links: [result.answer.link, ...(message.links || [])] });
        return result;
    }, [linkMessage, replace]);

    const undoLink = useCallback(async (message, link) => {
        const undone = await setLinkUndone(link.change_id, true);
        if (undone) {
            replace({
                ...message,
                links: message.links.map((item) => item.change_id === link.change_id ? { ...item, undone: true } : item),
            });
        }
        return undone;
    }, [setLinkUndone, replace]);

    const dismiss = useCallback(async (message, dismissed) => {
        const saved = await setDismissed(message.id, dismissed);
        if (saved) replace(saved);
        return saved;
    }, [setDismissed, replace]);

    return { link, undoLink, dismiss };
}
