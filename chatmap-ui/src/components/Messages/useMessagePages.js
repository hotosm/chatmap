import { useCallback, useEffect, useRef, useState } from "react";
import { useInterval } from "../../hooks/useInterval.js";

import useMessagesApi from "./useMessagesApi.js";
import { PAGE_SIZE, startsOver, withMessage } from "./messages.js";
import { newerInOrder, nextPageInOrder, olderInOrder, withShownRanks } from "./order.js";

// asOf: when what was reviewed is taken for the stretches of the list (see order.js), as its first page said
const EMPTY = { messages: [], more: false, asOf: null };
// How often the newest messages are read again while the page is in sight
const REFRESH_EVERY = 15 * 1000;

/**
 * The messages of a map, of one group or all of them (groupId null), and
 * all the ones not dismissed or only new, linked or dismissed ones (state):
 * in the order of the API (see order.js), a page at a time; the newest read again every few seconds
 * while the page is in sight, when it comes back in sight, and on asking (readNewer).
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
            setPage({ messages: answer.messages, more: answer.messages.length >= PAGE_SIZE, asOf: answer.as_of });
        });
        return () => { current = false; };
    }, [mapId, groupId, state, version, readMessages]);

    // The newest ones read again, on top of what is shown; one reading at a time
    const reading = useRef(false);
    const readNewer = useCallback(async () => {
        if (reading.current) return;
        reading.current = true;
        const question = asking.current;
        const answer = await readMessages(mapId, question);
        reading.current = false;
        if (!answer || !stillAsked(question)) return;
        setPage((shown) => startsOver(shown.messages, answer.messages) ?
            { messages: answer.messages, more: true, asOf: answer.as_of } :
            { ...shown, messages: newerInOrder(shown.messages, answer.messages, shown.more) });
    }, [mapId, readMessages]);

    // Every few seconds while the page is in sight, and as soon as it is back in sight
    const [inSight, setInSight] = useState(() => document.visibilityState !== "hidden");
    useEffect(() => {
        const seen = () => {
            const visible = document.visibilityState !== "hidden";
            setInSight(visible);
            if (visible) readNewer();
        };
        document.addEventListener("visibilitychange", seen);
        window.addEventListener("focus", seen);
        return () => {
            document.removeEventListener("visibilitychange", seen);
            window.removeEventListener("focus", seen);
        };
    }, [readNewer]);
    useInterval(readNewer, inSight ? REFRESH_EVERY : null);

    const loadMore = useCallback(async () => {
        const question = asking.current;
        setLoading(true);
        const answer = await readMessages(mapId, { ...question, ...nextPageInOrder(page.messages, page.asOf) });
        setLoading(false);
        if (!stillAsked(question)) return;
        if (!answer) {
            setError(true);
            return;
        }
        setError(false);
        setPage((shown) => ({
            ...shown,
            messages: olderInOrder(shown.messages, answer.messages),
            more: answer.messages.length >= PAGE_SIZE,
        }));
    }, [mapId, page.messages, page.asOf, readMessages]);

    const reload = useCallback(() => setVersion((version) => version + 1), []);

    // A message as it is after a change (linked, dismissed), in its place and with its rank: it moves when read again
    const replace = useCallback((message) => setPage((shown) => ({
        ...shown, messages: withMessage(shown.messages, withShownRanks(shown.messages, [message])[0]),
    })), []);

    return { messages: page.messages, more: page.more, loading, error, loadMore, reload, replace, readNewer };
}
