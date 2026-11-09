import { useCallback, useEffect, useRef, useState } from "react";
import { useInterval } from "../../hooks/useInterval.js";

import useMessagesApi from "./useMessagesApi.js";
import { PAGE_SIZE, nextPage, startsOver, withMessage, withNewer, withOlder } from "./messages.js";

const EMPTY = { messages: [], more: false };

/**
 * The messages of a map, of one group or all of them (groupId null), and
 * all the ones not dismissed or only new, linked or dismissed ones (state):
 * newest first, a page at a time, and read again every minute.
 *
 * @param {string} mapId The map
 * @param {string|null} groupId The group read
 * @param {string|null} state "new", "linked", "dismissed", or null
 */
export default function useMessagePages(mapId, groupId, state) {
    const { readMessages } = useMessagesApi();
    // Changes when the messages have to be read again from the first page (a group stopped, for one)
    const [version, setVersion] = useState(0);
    const [page, setPage] = useState(EMPTY);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(false);
    // What is asked for now: an answer for something else arrives late and is dropped
    const asked = { group_id: groupId, state };
    const asking = useRef(asked);
    asking.current = asked;
    const stillAsked = (question) => asking.current.group_id === question.group_id && asking.current.state === question.state;

    // The first page, when it opens, the group changes or it is read again
    useEffect(() => {
        let current = true;
        setPage(EMPTY);
        setError(false);
        setLoading(true);
        readMessages(mapId, { group_id: groupId, state }).then((answer) => {
            if (!current) return;
            setLoading(false);
            if (!answer) {
                setError(true);
                return;
            }
            setPage({ messages: answer.messages, more: answer.messages.length >= PAGE_SIZE });
        });
        return () => { current = false; };
    }, [mapId, groupId, state, version, readMessages]);

    // The newest ones, every minute
    useInterval(async () => {
        const question = asking.current;
        const answer = await readMessages(mapId, question);
        if (!answer || !stillAsked(question)) return;
        setPage((shown) => startsOver(shown.messages, answer.messages) ?
            { messages: answer.messages, more: true } :
            { ...shown, messages: withNewer(shown.messages, answer.messages) });
    }, 60 * 1000);

    const loadMore = useCallback(async () => {
        const question = asking.current;
        setLoading(true);
        const answer = await readMessages(mapId, { ...question, ...nextPage(page.messages) });
        setLoading(false);
        if (!stillAsked(question)) return;
        if (!answer) {
            setError(true);
            return;
        }
        setError(false);
        setPage((shown) => ({
            messages: withOlder(shown.messages, answer.messages),
            more: answer.messages.length >= PAGE_SIZE,
        }));
    }, [mapId, page.messages, readMessages]);

    const reload = useCallback(() => setVersion((version) => version + 1), []);

    // A message as it is after a change (linked, dismissed), in its place
    const replace = useCallback((message) => setPage((shown) => ({ ...shown, messages: withMessage(shown.messages, message) })), []);

    return { messages: page.messages, more: page.more, loading, error, loadMore, reload, replace };
}
