import { useCallback, useEffect, useRef, useState } from "react";
import { useInterval } from "../../hooks/useInterval.js";

import useMessagesApi from "./useMessagesApi.js";
import { PAGE_SIZE, nextPage, startsOver, withNewer, withOlder } from "./messages.js";

const EMPTY = { messages: [], more: false };

/**
 * The messages of a map, of one group or all of them (groupId null):
 * newest first, a page at a time, and read again every minute.
 *
 * @param {string} mapId The map
 * @param {string|null} groupId The group read
 */
export default function useMessagePages(mapId, groupId) {
    const { readMessages } = useMessagesApi();
    // Changes when the messages have to be read again from the first page (a group stopped, for one)
    const [version, setVersion] = useState(0);
    const [page, setPage] = useState(EMPTY);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(false);
    // The group asked for now: an answer for another one arrives late and is dropped
    const asking = useRef(groupId);
    asking.current = groupId;

    // The first page, when it opens, the group changes or it is read again
    useEffect(() => {
        let current = true;
        setPage(EMPTY);
        setError(false);
        setLoading(true);
        readMessages(mapId, { group_id: groupId }).then((answer) => {
            if (!current) return;
            setLoading(false);
            if (!answer) {
                setError(true);
                return;
            }
            setPage({ messages: answer.messages, more: answer.messages.length >= PAGE_SIZE });
        });
        return () => { current = false; };
    }, [mapId, groupId, version, readMessages]);

    // The newest ones, every minute
    useInterval(async () => {
        const asked = groupId;
        const answer = await readMessages(mapId, { group_id: asked });
        if (!answer || asking.current !== asked) return;
        setPage((shown) => startsOver(shown.messages, answer.messages) ?
            { messages: answer.messages, more: true } :
            { ...shown, messages: withNewer(shown.messages, answer.messages) });
    }, 60 * 1000);

    const loadMore = useCallback(async () => {
        const asked = groupId;
        setLoading(true);
        const answer = await readMessages(mapId, { group_id: asked, ...nextPage(page.messages) });
        setLoading(false);
        if (asking.current !== asked) return;
        if (!answer) {
            setError(true);
            return;
        }
        setError(false);
        setPage((shown) => ({
            messages: withOlder(shown.messages, answer.messages),
            more: answer.messages.length >= PAGE_SIZE,
        }));
    }, [mapId, groupId, page.messages, readMessages]);

    const reload = useCallback(() => setVersion((version) => version + 1), []);

    return { messages: page.messages, more: page.more, loading, error, loadMore, reload };
}
