import { expect, test as it } from 'vitest'

import {
  MAX_GROUP_PLACES, PAGE_SIZE, coordsOf, dayOf, groupMessagesOn, groupNames, groupPlaces, highlighted, linksOfPoint,
  liveLinks, messagesOn, metersBetween, nearestPlace, nextPage, pageOf, placesNamed, placesOf, placesToAdd, senderOf, startsOver,
  withMessage, withNewer, withOlder, linkOf, messageRows, renewable,
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

// linksOfPoint
it('keeps the changes of a point that came from messages and were not undone', () => {
  const changes = [
    { id: 3, source: "message", undone_at: null },
    { id: 2, source: "manual", undone_at: null },
    { id: 1, source: "message", undone_at: "2026-10-26T10:00:00Z" },
  ];
  expect(linksOfPoint({ changes }).map((change) => change.id)).toEqual([3]);
  expect(linksOfPoint(null)).toEqual([]);
});

// highlighted
const marks = (text, values) => highlighted(text, values).filter((piece) => piece.match).map((piece) => piece.text);

it('marks what a rule looked for, without minding case nor accents', () => {
  expect(marks("Está CERRADA la ruta", ["cerrada"])).toEqual(["CERRADA"]);
  expect(marks("cerrado el acceso", ["cérrado", "acceso"])).toEqual(["cerrado", "acceso"]);
  expect(highlighted("todo bien", ["cerrado"])).toEqual([{ text: "todo bien", match: false }]);
});

it('marks a word stretched to stress it, and Arabic with its marks, as the text says them', () => {
  expect(marks("está cerrrrrada!", ["cerrada"])).toEqual(["cerrrrrada"]);
  expect(marks("الحاجز مُسَكَّر اليوم", ["مسكر"])).toEqual(["مُسَكَّر"]);
  expect(marks("المعبر مسكـــر", ["مسكر"])).toEqual(["مسكـــر"]);
  expect(marks("طريق ٦٠ مغلق", ["60"])).toEqual(["٦٠"]);
});

it('keeps the whole text in its pieces', () => {
  const text = "Ya abrieron, estaba cerrado";
  expect(highlighted(text, ["cerrado", "abrieron"]).map((piece) => piece.text).join("")).toBe(text);
});

// senderOf, dayOf, nearestPlace
it('tells senders apart with the start of their pseudonym and a color of their own, always the same', () => {
  expect(senderOf("3fa1b2c3d4e5")).toEqual(senderOf("3fa1b2c3d4e5"));
  expect(senderOf("3fa1b2c3d4e5").code).toBe("3fa1");
  expect(senderOf("3fa1b2c3d4e5").hue).not.toBe(senderOf("9c0d11aa22bb").hue);
  expect(senderOf(undefined).code).toBe("");
});

it('gives the day a message was sent where the page is read', () => {
  expect(dayOf(new Date(2026, 9, 27, 23, 59))).toBe("2026-10-27");
  expect(dayOf(new Date(2026, 0, 5, 0, 1))).toBe("2026-01-05");
});

it('finds the place nearest to a location, within a distance', () => {
  expect(nearestPlace(features, [-34.5991, -58.3819]).name).toBe("Acceso norte");
  expect(nearestPlace(features, [-34.70, -58.50])).toBeNull();
  expect(nearestPlace(features, null)).toBeNull();
});

// groupPlaces, placesToAdd
const mapPlaces = [{ id: "p-1", name: "Acceso norte" }, { id: "p-2", name: "Acceso sur" }, { id: "p-3", name: "Plaza" }];

it('gives the places a group always speaks of, leaving out the ones the map no longer has', () => {
  expect(groupPlaces({ point_ids: ["p-2", "gone"] }, mapPlaces)).toEqual([{ id: "p-2", name: "Acceso sur" }]);
  expect(groupPlaces({}, mapPlaces)).toEqual([]);
});

it('offers the places a group can still have, found by name and without the chosen ones', () => {
  expect(placesToAdd(mapPlaces, ["p-1"], "acceso").map((place) => place.id)).toEqual(["p-2"]);
  expect(placesToAdd(mapPlaces, [], "").map((place) => place.id)).toEqual(["p-1", "p-2", "p-3"]);
});

it('offers none once a group has as many places as it can', () => {
  const full = mapPlaces.slice(0, MAX_GROUP_PLACES).map((place) => place.id);
  expect(placesToAdd(mapPlaces, full, "")).toEqual([]);
});

// messageRows, renewable

const line = (id, changes = {}) => ({ id, line: 0, point_id: "p-1", key_id: "k-1", value_id: "v-1", words: [], doubt: null, state: "pending", unchanged: false, ...changes });

it("marks the right words after an emoji written with two code units, as 🔴 is", () => {
  const marked = (text, values) => highlighted(text, values).filter((piece) => piece.match).map((piece) => piece.text);
  expect(marked("🔴 Azul cerrado", ["Azul", "cerrado"])).toEqual(["Azul", "cerrado"]);
  expect(marked("🔴🔴 Norte\n✅ Puente abierto", ["Puente", "🔴"])).toEqual(["🔴🔴", "Puente"]);
});

it("gives a message as rows: what rules suggest for the whole of it, then each line with text and what it says", () => {
  const rule = line("r", { line: null, rule: "North closed" });
  const rows = messageRows("Buen día\n\n✅ Puente abierto  \n🔴 Norte", [rule, line("a", { line: 2 }), line("b", { line: 2 })]);
  expect(rows.map((row) => [row.line, row.text, row.suggestions.map((item) => item.id)])).toEqual([
    [null, null, ["r"]], [0, "Buen día", []], [2, "✅ Puente abierto", ["a", "b"]], [3, "🔴 Norte", []],
  ]);
  expect(messageRows("hola", [])).toEqual([{ line: 0, text: "hola", suggestions: [] }]);
});

it("renews with one click only what is pending, plain, complete and already shown", () => {
  const same = line("same", { unchanged: true });
  expect(renewable([
    same, line("change"), line("asks", { unchanged: true, doubt: "question" }),
    line("answered", { unchanged: true, state: "accepted" }), line("no value", { unchanged: true, value_id: null }),
  ])).toEqual([same]);
});

it("finds the link a confirmed suggestion made, not an undone one nor one of another value", () => {
  const message = { links: [
    { change_id: 1, point_id: "p-1", key_id: "k-1", value_id: "v-2", undone: false },
    { change_id: 2, point_id: "p-1", key_id: "k-1", value_id: "v-1", undone: true },
    { change_id: 3, point_id: "p-1", key_id: "k-1", value_id: "v-1", undone: false },
  ] };
  expect(linkOf(message, line("a")).change_id).toBe(3);
  // A suggestion of only the place, by any link to it
  expect(linkOf(message, line("b", { key_id: null, value_id: null })).change_id).toBe(1);
  expect(linkOf(message, line("c", { point_id: "p-9" }))).toBeNull();
});
