import { expect, test as it } from 'vitest'

import {
  EXPIRED, OLDER, ON_MAP, TAKEN_OUT, UNDONE, noteOf, placeHistory, valueOf, valuesInForce,
} from '../src/components/Messages/placeHistory';

const NOW = new Date("2026-11-09T12:00:00Z").getTime();
const hoursAgo = (hours) => new Date(NOW - hours * 60 * 60 * 1000).toISOString();

const STATUS = {
  id: "k-status", key: "Status", single: true, closed: true,
  values: [
    { id: "v-open", value: "Open", color: "#2BA8A0", expires_after: 24 },
    { id: "v-closed", value: "Closed", color: "#D63F40", expires_after: 24 },
  ],
};
const DIRECTION = {
  id: "k-direction", key: "Direction", single: true, closed: true,
  values: [{ id: "v-one-way", value: "One-way", color: "#1F2329", expires_after: null }],
};
const NOTES = { id: "k-notes", key: "Notes", single: false, closed: false, values: [] };
const KEYS = [STATUS, DIRECTION, NOTES];

const tag = (key_id, value_id, hours, value = null) =>
  ({ key_id, value_id, value, since: hoursAgo(hours), confirmed_at: hoursAgo(hours) });
const change = (id, key_id, value_id, hours, extra = {}) => ({
  id, key_id, key: key_id, action: "set", value_id, value: null, happened_at: hoursAgo(hours),
  source: "message", message_id: `m-${id}`, undone_at: null, ...extra,
});

// The road of the design: closed 10 minutes ago, one-way for two days
const TAGS = [tag("k-status", "v-closed", 1 / 6), tag("k-direction", "v-one-way", 48)];
const CHANGES = [
  change(5, "k-status", "v-closed", 13, { undone_at: hoursAgo(12) }),
  change(4, "k-status", "v-open", 12),
  change(3, "k-status", "v-open", 3, { source: "manual", message_id: null }),
  change(6, "k-direction", "v-one-way", 48, { message_id: null }),
  change(1, "k-status", "v-closed", 1 / 6),
];

// valuesInForce
it('tells what the map shows for each key of a place, in the order of the keys', () => {
  const rows = valuesInForce(TAGS, KEYS, NOW);

  expect(rows.map(({ key, values }) => [key.key, values.map(({ value }) => value.value)])).toEqual([
    ["Status", ["Closed"]], ["Direction", ["One-way"]],
  ]);
});
it('tells when a value stops being known, and that one without expiry never does', () => {
  const [status, direction] = valuesInForce(TAGS, KEYS, NOW);

  expect(status.values[0].expiresAt.toISOString()).toBe(new Date(new Date(hoursAgo(1 / 6)).getTime() + 24 * 3600 * 1000).toISOString());
  expect(status.values[0].expired).toBe(false);
  expect(direction.values[0].expiresAt).toBe(null);
});
it('marks a value nobody confirmed for longer than it lasts as expired', () => {
  const [status] = valuesInForce([tag("k-status", "v-open", 30)], KEYS, NOW);
  expect(status.values[0].expired).toBe(true);
});
it('keeps the many values of a key together, and a written one as a text', () => {
  const rows = valuesInForce([tag("k-notes", null, 1, "gate"), tag("k-notes", null, 2, "mud")], KEYS, NOW);
  expect(rows).toHaveLength(1);
  expect(rows[0].values.map(({ value }) => value.value)).toEqual(["gate", "mud"]);
});

// placeHistory
it('orders the changes of a place newest first, whatever order they come in', () => {
  expect(placeHistory(CHANGES, TAGS, KEYS, NOW).map(({ change }) => change.id)).toEqual([1, 3, 4, 5, 6]);
});
it('tells which change rules, which are older and which were undone', () => {
  const states = Object.fromEntries(placeHistory(CHANGES, TAGS, KEYS, NOW).map(({ change, state }) => [change.id, state]));
  expect(states).toEqual({ 1: ON_MAP, 3: OLDER, 4: OLDER, 5: UNDONE, 6: ON_MAP });
});
it('puts on the map the newest change of a value, not an older one that said the same', () => {
  const changes = [change(2, "k-status", "v-closed", 1), change(1, "k-status", "v-closed", 5)];
  const states = placeHistory(changes, [tag("k-status", "v-closed", 1)], KEYS, NOW).map(({ state }) => state);
  expect(states).toEqual([ON_MAP, OLDER]);
});
it('does not put on the map an undone change, even the newest of its value', () => {
  const changes = [change(2, "k-status", "v-closed", 1, { undone_at: hoursAgo(0.5) }), change(1, "k-status", "v-closed", 5)];
  const states = placeHistory(changes, [tag("k-status", "v-closed", 5)], KEYS, NOW).map(({ state }) => state);
  expect(states).toEqual([UNDONE, ON_MAP]);
});
it('marks the change of a value that expired', () => {
  const [entry] = placeHistory([change(1, "k-status", "v-open", 30)], [tag("k-status", "v-open", 30)], KEYS, NOW);
  expect(entry.state).toBe(EXPIRED);
});
it('marks a change that took a value out', () => {
  const [entry] = placeHistory([change(1, "k-status", "v-open", 1, { action: "remove" })], [], KEYS, NOW);
  expect(entry.state).toBe(TAKEN_OUT);
});
it('tells a change from a message that is no longer kept, but not one made by hand', () => {
  const gone = Object.fromEntries(placeHistory(CHANGES, TAGS, KEYS, NOW).map(({ change, gone }) => [change.id, gone]));
  expect(gone).toEqual({ 1: false, 3: false, 4: false, 5: false, 6: true });
});
it('finds the value of a change in its key, with its color, or keeps the name it had', () => {
  expect(valueOf(STATUS, { value_id: "v-open" }).color).toBe("#2BA8A0");
  expect(valueOf(STATUS, { value_id: "v-gone", value: "Flooded" })).toEqual({ value: "Flooded" });
  expect(valueOf(undefined, { value_id: null, value: "gate" })).toEqual({ value: "gate" });
});

// noteOf
it('says first that a change was undone, then that its message is gone, then how it was made', () => {
  const notes = Object.fromEntries(placeHistory(CHANGES, TAGS, KEYS, NOW).map((entry) => [entry.change.id, noteOf(entry)]));
  expect(notes).toEqual({ 1: "linked", 3: "manual", 4: "older", 5: "undone", 6: "gone" });
});
it('tells a link a rule suggested, a value taken out and a change the system made', () => {
  const entry = (extra, state = ON_MAP) => ({ change: change(1, "k-status", "v-open", 1, extra), state, gone: false });
  expect(noteOf(entry({ source: "rule" }))).toBe("byRule");
  expect(noteOf(entry({ action: "remove" }, TAKEN_OUT))).toBe("takenOut");
  expect(noteOf(entry({ source: "system", message_id: null }))).toBe("other");
});
