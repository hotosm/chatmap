import { expect, test as it } from 'vitest'

import {
  EXPIRED, OLDER, ageOf, boundsOf, hoursAs, linkOutcome, onlyLocation, placeAt, placesCoords, statusKeyOf,
  statusOf,
} from '../src/components/Messages/linkStates';

const NOW = new Date("2026-11-09T12:00:00Z").getTime();
const OPEN = { id: "v-open", value: "Open", color: "#3E9E47", expires_after: 4 };
const CLOSED = { id: "v-closed", value: "Closed", color: "#D73F3F", expires_after: null };
const RESTRICTED = { id: "v-restricted", value: "Restricted", color: "#E9A23B", expires_after: 24 };
const STATUS = { id: "k-status", key: "Status", single: true, closed: true, colors_map: true, values: [OPEN, CLOSED, RESTRICTED] };
const NOTES = { id: "k-notes", key: "Notes", single: false, closed: false, colors_map: false, values: [] };
const LINK = { change_id: 7, point_id: "p-1", key_id: "k-status", value_id: "v-closed", value: "Closed", undone: false };
const tag = (value_id, confirmed_at) => ({ point_id: "p-1", key_id: "k-status", value_id, value: null, since: confirmed_at, confirmed_at });

// hoursAs
it('should say the hours a value lasts in hours up to two days', () => {
  expect(hoursAs(4)).toEqual({ value: 4, unit: "hour" });
  expect(hoursAs(24)).toEqual({ value: 24, unit: "hour" });
  expect(hoursAs(36)).toEqual({ value: 36, unit: "hour" });
});
it('should say whole days from two days on', () => {
  expect(hoursAs(48)).toEqual({ value: 2, unit: "day" });
  expect(hoursAs(72)).toEqual({ value: 3, unit: "day" });
});

// ageOf
it('should say how old something is, forward', () => {
  expect(ageOf("2026-11-07T11:00:00Z", NOW)).toEqual({ value: 2, unit: "day" });
  expect(ageOf("2026-11-09T11:40:00Z", NOW)).toEqual({ value: 20, unit: "minute" });
  expect(ageOf("2026-11-09T11:59:50Z", NOW)).toEqual({ value: 0, unit: "minute" });
});

// linkOutcome
it('should say nothing when the place shows the value of the message', () => {
  const answer = { link: LINK, tags: [tag("v-closed", "2026-11-09T09:00:00Z")], applied: true };
  expect(linkOutcome({ answer, key: STATUS, value: CLOSED, sentAt: "2026-11-09T09:00:00Z", now: NOW })).toBe(null);
});
it('should say the newer value the place keeps showing, and since when', () => {
  const answer = { link: LINK, tags: [tag("v-open", "2026-11-09T11:40:00Z")], applied: false };
  expect(linkOutcome({ answer, key: STATUS, value: CLOSED, sentAt: "2026-11-09T09:00:00Z", now: NOW })).toEqual({
    kind: OLDER, link: LINK, shown: OPEN, shownAt: "2026-11-09T11:40:00Z",
  });
});
it('should take the value confirmed last when the place has many', () => {
  const answer = {
    link: LINK, applied: false,
    tags: [tag("v-closed", "2026-11-09T10:00:00Z"), tag("v-open", "2026-11-09T11:40:00Z"), { ...tag("x", "2026-11-09T11:59:00Z"), key_id: "other" }],
  };
  expect(linkOutcome({ answer, key: STATUS, value: CLOSED, sentAt: "2026-11-09T09:00:00Z", now: NOW }).shown).toBe(OPEN);
});
it('should not say a newer value that expired too, nor one it does not know', () => {
  const expired = { link: LINK, tags: [tag("v-open", "2026-11-09T06:00:00Z")], applied: false };
  expect(linkOutcome({ answer: expired, key: STATUS, value: CLOSED, sentAt: "2026-11-09T05:00:00Z", now: NOW }))
    .toEqual({ kind: OLDER, link: LINK, shown: null, shownAt: null });
  const none = { link: LINK, tags: [], applied: false };
  expect(linkOutcome({ answer: none, key: STATUS, value: CLOSED, sentAt: "2026-11-09T05:00:00Z", now: NOW }).shown).toBe(null);
});
it('should say a written value the place has now as it was written', () => {
  const answer = {
    link: LINK, applied: false,
    tags: [{ point_id: "p-1", key_id: "k-notes", value_id: null, value: "Long queue", since: "2026-11-09T11:00:00Z", confirmed_at: "2026-11-09T11:00:00Z" }],
  };
  expect(linkOutcome({ answer, key: NOTES, value: null, sentAt: "2026-11-09T09:00:00Z", now: NOW }).shown).toEqual({ value: "Long queue" });
});
it('should say a value that already expired, how long it lasts and how old the message is', () => {
  const answer = { link: LINK, tags: [tag("v-restricted", "2026-11-07T11:00:00Z")], applied: true };
  expect(linkOutcome({ answer, key: STATUS, value: RESTRICTED, sentAt: "2026-11-07T11:00:00Z", now: NOW })).toEqual({
    kind: EXPIRED, link: LINK, value: RESTRICTED, lasts: { value: 24, unit: "hour" }, age: { value: 2, unit: "day" },
  });
});
it('should say nothing of a value that does not expire', () => {
  const answer = { link: LINK, tags: [tag("v-closed", "2026-10-01T00:00:00Z")], applied: true };
  expect(linkOutcome({ answer, key: STATUS, value: CLOSED, sentAt: "2026-10-01T00:00:00Z", now: NOW })).toBe(null);
});

// onlyLocation
it('should know a message that is only a location', () => {
  expect(onlyLocation({ text: "", location: "-34.6037, -58.3816" })).toBe(true);
  expect(onlyLocation({ text: "  \n", location: "-34.6037, -58.3816" })).toBe(true);
  expect(onlyLocation({ text: null, location: "-34.6037, -58.3816" })).toBe(true);
});

// statusKeyOf / statusOf
it('should show the value of the key the map is colored by, or else of the first that could color it', () => {
  expect(statusKeyOf([NOTES, STATUS])).toBe(STATUS);
  expect(statusKeyOf([NOTES, { ...STATUS, colors_map: false }]).id).toBe("k-status");
  expect(statusKeyOf([NOTES])).toBe(null);
});
it('should say what a place shows now for the key', () => {
  const feature = (point_tags) => ({ properties: { id: "p-1", point_tags } });
  expect(statusOf(feature([tag("v-closed", "2026-11-09T09:00:00Z")]), STATUS, NOW)).toBe(CLOSED);
  expect(statusOf(feature([tag("v-open", "2026-11-09T06:00:00Z")]), STATUS, NOW)).toEqual({
    unknown: true, last: OPEN, expiredAt: new Date("2026-11-09T10:00:00Z"),
  });
  expect(statusOf(feature([]), STATUS, NOW)).toBe(null);
  expect(statusOf(feature([tag("v-closed", "2026-11-09T09:00:00Z")]), null, NOW)).toBe(null);
  expect(statusOf(undefined, STATUS, NOW)).toBe(null);
});

// placeAt
it('should put a new place where the message was sent from, longitude first as the map takes it', () => {
  const { request, featureOf } = placeAt("South gate", [-34.6037, -58.3816], "2026-11-09T12:00:00Z");
  expect(request).toEqual({ longitude: -58.3816, latitude: -34.6037, time: "2026-11-09T12:00:00Z", message: "South gate" });
  expect(featureOf("p-new").geometry.coordinates).toEqual([-58.3816, -34.6037]);
});

// boundsOf, placesCoords: where the small map starts when a new place is pointed on it

it('fits the places of the map, west to east and south to north', () => {
  expect(boundsOf([[-34.6, -58.38], [-34.59, -58.4], null])).toEqual([[-58.4, -34.6], [-58.38, -34.59]]);
  expect(boundsOf([])).toBe(null);
});

it('tells where the places of the map are, without the removed ones', () => {
  const feature = (lon, lat, removed = false) => ({ properties: { removed }, geometry: { coordinates: [lon, lat] } });
  expect(placesCoords([feature(-58.38, -34.6), feature(-58.4, -34.59, true)])).toEqual([[-34.6, -58.38]]);
});
