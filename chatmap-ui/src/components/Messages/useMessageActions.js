import { useCallback } from "react";

import { withSuggestions } from "./messages.js";
import useMessagesApi from "./useMessagesApi.js";

/**
 * What the owner of a map does with a message: link it to a point, undo a
 * link, dismiss it or bring it back, answer what it suggests. Each one gives the message as it is
 * after it to `replace`, and answers null when the API does not take it
 * (link answers the status too, to tell why).
 *
 * @param {function} replace Gets a message after a change
 */
export default function useMessageActions(replace) {
    const {
        linkMessage, setLinkUndone, setDismissed, setLineSuggestionRejected, renewSuggestions,
    } = useMessagesApi();

    // { status, answer }; answer is { link, tags, applied }, and applied is false when the point had something newer
    const link = useCallback(async (message, change) => {
        const result = await linkMessage(message.id, change);
        if (result.answer) {
            // A link answers what the message suggested for its place and key, as the API gives them back
            replace(withSuggestions(
                { ...message, links: [result.answer.link, ...(message.links || [])] }, result.answer.suggestions,
            ));
        }
        return result;
    }, [linkMessage, replace]);


    // No to what a message suggests (rejected true), or that taken back
    const answerLine = useCallback(async (message, suggestion, rejected) => {
        const saved = await setLineSuggestionRejected(suggestion.id, rejected);
        if (saved) replace(withSuggestions(message, saved.suggestions));
        return saved;
    }, [setLineSuggestionRejected, replace]);

    // Yes, with one click, to what lines say that their places already show: { links, suggestions }
    const renew = useCallback(async (message, suggestions) => {
        const saved = await renewSuggestions(message.id, suggestions.map((item) => item.id));
        // Each one renewed is a link of the message, as a link made by hand
        if (saved) replace(withSuggestions({ ...message, links: [...(saved.links || []), ...(message.links || [])] }, saved.suggestions));
        return saved;
    }, [renewSuggestions, replace]);

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

    return { link, undoLink, dismiss, answerLine, renew };
}
