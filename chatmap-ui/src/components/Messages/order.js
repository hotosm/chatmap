import { nextPage, withNewer, withOlder } from "./messages.js";

/**
 * The order of all the messages and the new ones, in two stretches, as the
 * API gives it (see rank in GroupMessageItem): first the ones sent after the
 * last one a person reviewed in their group; then the older ones. Within a rank, newest first. The other reads have
 * no rank and go newest first.
 */
// Sent before it, or when it was: the second stretch
export const BEFORE_REVIEWED = 0;

const rankOf = (message) => message.rank ?? BEFORE_REVIEWED;

/**
 * The order of two messages: by rank, then newest first. Messages sent in
 * the same second stay as they are: the API orders them by id as the
 * database does, which is not how they compare here.
 */
export const byRank = (a, b) => rankOf(b) - rankOf(a) || Date.parse(b.sent_at) - Date.parse(a.sent_at);

// The messages in order; sort keeps the ones that compare the same as they were
export const inOrder = (messages) => [...messages].sort(byRank);

// The messages without repeating one: the first of each id stays
export const unique = (messages) => {
    const seen = new Set();
    return messages.filter((message) => !seen.has(message.id) && seen.add(message.id));
};

/**
 * The messages with the rank they have where they are shown: a message
 * linked or dismissed (here or in another tab) changes the stretches of
 * its group, but nothing moves under the reader until the list is read again.
 */
export const withShownRanks = (shown, messages) => {
    const ranks = new Map(shown.map((message) => [message.id, message.rank]));
    return messages.map((message) => ranks.has(message.id) ? { ...message, rank: ranks.get(message.id) } : message);
};

/**
 * The messages shown after reading the newest ones again. Those not shown
 * yet go in only when they do not come after the last one shown (or nothing
 * else is left to read): one further down will come with the next pages,
 * which start after the last one shown and must not skip any. One sent in
 * the same second as it goes in, since only the API knows which comes first.
 */
export const newerInOrder = (shown, page, more) => {
    const last = shown[shown.length - 1];
    const shownIds = new Set(shown.map((message) => message.id));
    const taken = withShownRanks(shown, page).filter((message) =>
        shownIds.has(message.id) || !more || !last || byRank(message, last) <= 0
    );
    return inOrder(unique(withNewer(shown, taken)));
};

// The messages shown after reading the next page, in order
export const olderInOrder = (shown, page) => inOrder(unique(withOlder(shown, page)));

/**
 * Where the next page starts: after the last message shown, by its rank
 * when it has one, its time and its id; with when what was reviewed is
 * taken (as_of, from the first page), so the stretches do not change between pages.
 */
export const nextPageInOrder = (shown, asOf) => {
    const last = shown[shown.length - 1];
    if (!last) return {};
    return {
        ...nextPage(shown),
        ...(last.rank != null && { before_rank: last.rank }),
        ...(asOf && { as_of: asOf }),
    };
};

// Whether the message at index starts the stretch of the ones sent before the last reviewed of their group
export const startsBeforeReviewed = (messages, index) =>
    index > 0 && messages[index].rank === BEFORE_REVIEWED && rankOf(messages[index - 1]) > BEFORE_REVIEWED;
