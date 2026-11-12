import { expect, test as it } from 'vitest'

import {
  PAGE_SIZE, coordsOf, groupMessagesOn, groupNames, liveLinks, messagesOn, metersBetween, nextPage, pageOf,
  placesNamed, placesOf, startsOver, withMessage, withNewer, withOlder,
} from '../src/components/Messages/messages';

const message = (id, sent_at) => ({ id, sent_at, group_id: "g-1", text: id });
// A full page, newest first, all sent in the same second as many can be
const fullPage = (sent_at, prefix) =>
  Array.from({ length: PAGE_SIZE }, (_, i) => message(`${prefix}-${String(PAGE_SIZE - i).padStart(3, "0")}`, sent_at));

// groupMessagesOn
it('should know the server keeps group messages from config.json, as a boolean or as text', () => {
  expect(groupMessagesOn({ ENABLE_GROUP_MESSAGES: true })).toBe(true);
  expect(groupMessagesOn({ ENABLE_GROUP_MESSAGES: "true" })).toBe(true);
});
it('should take a server without the setting as not keeping them', () => {
  expect(groupMessagesOn({ ENABLE_GROUP_MESSAGES: "false" })).toBe(false);
  expect(groupMessagesOn({ ENABLE_GROUP_MESSAGES: "" })).toBe(false);
  expect(groupMessagesOn({})).toBe(false);
});

// messagesOn
it('should show the messages to the owner of a map shown with its keys', () => {
  expect(messagesOn({ id: "map-1", owner: true }, true)).toBe(true);
});
it('should not show the messages to anyone else', () => {
  expect(messagesOn({ id: "map-1", owner: false }, true)).toBe(false);
});
it('should not show the messages of a map shown without its keys', () => {
  expect(messagesOn({ id: "map-1", owner: true }, false)).toBe(false);
});

// withNewer / withOlder
it('should put the newest messages read again on top, each message once', () => {
  const shown = [message("b", "2026-10-22T12:01:00Z"), message("a", "2026-10-22T12:00:00Z")];
  const page = [message("c", "2026-10-22T12:02:00Z"), message("b", "2026-10-22T12:01:00Z")];
  expect(withNewer(shown, page).map((m) => m.id)).toEqual(["c", "b", "a"]);
});
it('should put the next page below, each message once', () => {
  const shown = [message("c", "2026-10-22T12:02:00Z"), message("b", "2026-10-22T12:01:00Z")];
  const page = [message("b", "2026-10-22T12:01:00Z"), message("a", "2026-10-22T12:00:00Z")];
  expect(withOlder(shown, page).map((m) => m.id)).toEqual(["c", "b", "a"]);
});
it('should keep the order the API gives to messages sent in the same second', () => {
  const second = "2026-10-22T12:00:00Z";
  // The database may order ids in a way the browser would not
  const shown = [message("x-2", second), message("X-1", second)];
  const page = [message("X-0", second), message("x-00", second)];
  expect(withOlder(shown, page).map((m) => m.id)).toEqual(["x-2", "X-1", "X-0", "x-00"]);
  expect(nextPage(withOlder(shown, page))).toEqual({ before: second, before_id: "x-00" });
});

// startsOver
it('should start over when a full page is all newer than what is shown', () => {
  const shown = [message("old", "2026-10-22T12:00:00Z")];
  expect(startsOver(shown, fullPage("2026-10-22T12:05:00Z", "new"))).toBe(true);
});
it('should not start over when the newest page reaches what is shown', () => {
  const page = fullPage("2026-10-22T12:05:00Z", "new");
  expect(startsOver([page[PAGE_SIZE - 1]], page)).toBe(false);
});
it('should not start over with a page that is not full', () => {
  expect(startsOver([message("old", "2026-10-22T12:00:00Z")], [message("new", "2026-10-22T12:05:00Z")])).toBe(false);
});
it('should not start over when nothing is shown', () => {
  expect(startsOver([], fullPage("2026-10-22T12:05:00Z", "new"))).toBe(false);
});

// nextPage
it('should ask for the next page after the time and id of the last message shown', () => {
  const shown = [message("b", "2026-10-22T12:01:00Z"), message("a", "2026-10-22T12:00:00Z")];
  expect(nextPage(shown)).toEqual({ before: "2026-10-22T12:00:00Z", before_id: "a" });
});
it('should ask for the first page when nothing is shown', () => {
  expect(nextPage([])).toEqual({});
});

// groupNames
it('should give the name of each group by its id', () => {
  expect(groupNames([{ id: "g-1", name: "North" }, { id: "g-2", name: "" }])).toEqual({ "g-1": "North", "g-2": "" });
  expect(groupNames(null)).toEqual({});
});

// coordsOf
it('should read the coordinates of a location, rounded to about a meter', () => {
  expect(coordsOf("-34.603722,-58.381592")).toEqual([-34.60372, -58.38159]);
  expect(coordsOf(" -34.6, -58.38 near the bridge")).toEqual([-34.6, -58.38]);
});
it('should not read coordinates where there are none, or out of range', () => {
  expect(coordsOf("near the bridge")).toBeNull();
  expect(coordsOf("95.1,10")).toBeNull();
  expect(coordsOf(null)).toBeNull();
});

// pageOf
it('should keep the parameters of the current page, like ?dashboard', () => {
  expect(pageOf("/map/map-1/messages", "#/map/map-1?dashboard")).toBe("#/map/map-1/messages?dashboard");
});
it('should go without parameters when the current page has none', () => {
  expect(pageOf("/map/map-1", "#/map/map-1/messages")).toBe("#/map/map-1");
});

// placesOf, placesNamed, metersBetween
const point = (id, name, [lon, lat], removed = false, place = true) =>
  ({ properties: { id, message: name, removed, place }, geometry: { type: "Point", coordinates: [lon, lat] } });
const features = [
  point("p-1", "Plaza", [-58.3800, -34.6000]),
  point("p-2", "Acceso norte", [-58.3820, -34.5990]),
  point("p-3", "Hospital viejo", [-58.3700, -34.6100], true),
  // A report from a location shared in a chat: not a place to link messages to
  point("r-1", "Cortado el acceso, pasen por el otro lado", [-58.3821, -34.5991], false, false),
];

it('measures meters between two places near enough', () => {
  expect(metersBetween([-34.6, -58.38], [-34.6, -58.38])).toBe(0);
  // A thousandth of a degree of latitude is about 111 meters
  expect(metersBetween([-34.6, -58.38], [-34.601, -58.38])).toBe(111);
});

it('lists the places a message can be linked to, nearest first when it says where it was sent from', () => {
  expect(placesOf(features, [-34.5991, -58.3819]).map((place) => place.id)).toEqual(["p-2", "p-1"]);
  expect(placesOf(features, [-34.5991, -58.3819])[0].meters).toBeLessThan(20);
});

it('lists them by name, without a removed one nor a report, when the message says nothing of where', () => {
  expect(placesOf(features, null)).toEqual([
    { id: "p-2", name: "Acceso norte", meters: null }, { id: "p-1", name: "Plaza", meters: null },
  ]);
});

it('finds places by name without minding case nor accents', () => {
  const places = [{ id: "p-1", name: "Estación Norte" }, { id: "p-2", name: "Plaza" }];
  expect(placesNamed(places, "  estacion ").map((place) => place.id)).toEqual(["p-1"]);
  expect(placesNamed(places, "")).toBe(places);
});

// liveLinks, withMessage
it('keeps the links of a message that were not undone', () => {
  const links = [{ change_id: 2, undone: false }, { change_id: 1, undone: true }];
  expect(liveLinks({ links })).toEqual([{ change_id: 2, undone: false }]);
  expect(liveLinks({})).toEqual([]);
});

it('puts a message as it is now in its place', () => {
  const shown = [{ id: "m-2", text: "a" }, { id: "m-1", text: "b" }];
  expect(withMessage(shown, { id: "m-1", text: "c" })).toEqual([{ id: "m-2", text: "a" }, { id: "m-1", text: "c" }]);
});
