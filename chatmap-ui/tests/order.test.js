import { expect, test as it } from 'vitest'

import { PAGE_SIZE } from '../src/components/Messages/messages';
import {
  byRank, inOrder, newerInOrder, nextPageInOrder, olderInOrder, startsBeforeReviewed, unique, withShownRanks,
} from '../src/components/Messages/order';

const at = (minute) => `2026-11-01T10:${String(minute).padStart(2, "0")}:00Z`;
const message = (id, minute, rank) => ({ id, sent_at: at(minute), rank, group_id: "g-1", text: id });
const ids = (messages) => messages.map((m) => m.id);

// byRank
it('should put the marked first, then the rest after the last reviewed, then the older ones, each newest first', () => {
  const messages = [message("old", 50, 0), message("rest", 20, 1), message("marked", 10, 2), message("rest2", 30, 1)];
  expect(ids([...messages].sort(byRank))).toEqual(["marked", "rest2", "rest", "old"]);
});
it('should leave messages of the same rank and second as the API gave them', () => {
  const messages = [message("b", 10, 1), message("a", 10, 1), message("C", 10, 1)];
  expect(ids(inOrder(messages))).toEqual(["b", "a", "C"]);
});
it('should order the reads without ranks newest first', () => {
  expect(ids(inOrder([message("a", 1, null), message("b", 2, null)]))).toEqual(["b", "a"]);
});

// unique
it('should keep each message once, the first of them', () => {
  const first = message("a", 1, 2);
  expect(unique([first, message("b", 1, 1), message("a", 1, 0)])).toEqual([first, message("b", 1, 1)]);
});

// olderInOrder
it('should put the next page below without repeating a message', () => {
  const shown = [message("m", 5, 2), message("r", 9, 1)];
  const page = [message("r", 9, 1), message("o", 8, 0)];
  expect(ids(olderInOrder(shown, page))).toEqual(["m", "r", "o"]);
});

// newerInOrder
it('should put a message that just arrived in its stretch: on top when marked, above the rest when not', () => {
  const shown = [message("m", 5, 2), message("r", 9, 1), message("o", 8, 0)];
  const page = [message("new-m", 20, 2), message("new", 21, 1), ...shown];
  expect(ids(newerInOrder(shown, page, false))).toEqual(["new-m", "m", "new", "r", "o"]);
});
it('should not move a message shown when its group was reviewed since', () => {
  const shown = [message("r2", 10, 1), message("r1", 9, 1)];
  // Read again, r2 was linked: now its group is cut there
  const page = [message("r2", 10, 0), message("r1", 9, 0)];
  expect(newerInOrder(shown, page, true).map((m) => [m.id, m.rank])).toEqual([["r2", 1], ["r1", 1]]);
});
it('should leave for the next pages a message read again that goes below the last one shown', () => {
  const shown = [message("r2", 10, 1), message("r1", 9, 1)];
  const page = [message("r2", 10, 1), message("r1", 9, 1), message("o", 8, 0)];
  expect(ids(newerInOrder(shown, page, true))).toEqual(["r2", "r1"]);
  expect(ids(newerInOrder(shown, page, false))).toEqual(["r2", "r1", "o"]);
});

// withShownRanks
it('should keep the rank a message has where it is shown after a change', () => {
  const shown = [message("a", 1, 2)];
  expect(withShownRanks(shown, [{ ...message("a", 1, null), dismissed_at: at(2) }])[0]).toMatchObject({ rank: 2, dismissed_at: at(2) });
  expect(withShownRanks(shown, [message("b", 1, 0)])[0].rank).toBe(0);
});

// nextPageInOrder
it('should start the next page after the rank, time and id of the last message, as of the first page', () => {
  const shown = [message("a", 2, 1), message("b", 1, 0)];
  expect(nextPageInOrder(shown, "2026-11-01T11:00:00.123456Z")).toEqual({
    before: at(1), before_id: "b", before_rank: 0, as_of: "2026-11-01T11:00:00.123456Z",
  });
});
it('should start the next page of a read without ranks after the time and id only', () => {
  expect(nextPageInOrder([message("a", 1, null)], "t")).toEqual({ before: at(1), before_id: "a", as_of: "t" });
  expect(nextPageInOrder([], "t")).toEqual({});
});

// startsBeforeReviewed
it('should mark where the older messages start, once', () => {
  const messages = [message("m", 5, 2), message("r", 9, 1), message("o1", 8, 0), message("o2", 7, 0)];
  expect(messages.map((_, index) => startsBeforeReviewed(messages, index))).toEqual([false, false, true, false]);
});
it('should not mark it when all of them are older, nor in the reads without ranks', () => {
  const older = [message("o1", 8, 0), message("o2", 7, 0)];
  expect(older.map((_, index) => startsBeforeReviewed(older, index))).toEqual([false, false]);
  const newestFirst = [message("a", 8, null), message("b", 7, null)];
  expect(newestFirst.map((_, index) => startsBeforeReviewed(newestFirst, index))).toEqual([false, false]);
});

// A full page read again keeps the order of the API
it('should keep a full page read again as the API ordered it', () => {
  const page = Array.from({ length: PAGE_SIZE }, (_, i) => message(`x-${i}`, 30, 1));
  expect(ids(newerInOrder([message("x-0", 30, 1)], page, true))).toEqual(ids(page));
});
