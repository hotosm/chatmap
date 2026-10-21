import { expect, test as it} from 'vitest'

import {
  colorKeyOf, colorKeys, expiresAt, freeTags, freeTagsInUse, keyFilter, keyFilterOf, keysOn, newPoint, shownValue,
  shownValueCounts, textOn, UNKNOWN, usesKeys, valuesInUse, withKeyTags, withShownValues, withTags,
} from '../src/components/Tags/tags';

const OPEN = { id: "v-open", value: "Open", color: "#3E9E47", expires_after: 4 };
const CLOSED = { id: "v-closed", value: "Closed", color: "#D73F3F", expires_after: null };
const STATUS = { id: "k-status", key: "Status", single: true, closed: true, colors_map: true, values: [OPEN, CLOSED] };
const NOTES = { id: "k-notes", key: "Notes", single: false, closed: false, colors_map: false, values: [] };

const at = (time) => new Date(`2026-10-19T${time}:00Z`).getTime();
const tag = (valueId, confirmed = "11:00") => ({
  key_id: STATUS.id, value_id: valueId, value: null, since: "2026-10-19T08:30:00Z", confirmed_at: `2026-10-19T${confirmed}:00Z`,
});

const mapData = {
  id: "map-1",
  features: [
    { type: "Feature", geometry: { type: "Point", coordinates: [1, 2] }, properties: { id: "p-1", message: "one" } },
    { type: "Feature", geometry: { type: "Point", coordinates: [3, 4] }, properties: { id: "p-2", message: "two" } },
  ],
};

// withTags
it('should add the keys of the map and what each point has', () => {
  const result = withTags(mapData, [STATUS, NOTES], [{ point_id: "p-1", ...tag(OPEN.id) }]);

  expect(result.keys).toEqual([STATUS, NOTES]);
  expect(result.features[0].properties.point_tags).toEqual([{ point_id: "p-1", ...tag(OPEN.id) }]);
  expect(result.features[1].properties.point_tags).toEqual([]);
  expect(result.features[0].properties.message).toEqual("one");
});
// colorKeyOf
it('should color the map by the key its owner chose until whoever looks chooses another or none', () => {
  const fuel = { ...STATUS, id: "k-fuel", colors_map: false };

  expect(colorKeyOf([NOTES, STATUS, fuel]).id).toEqual("k-status");
  expect(colorKeyOf([NOTES, STATUS, fuel], "k-fuel").id).toEqual("k-fuel");
  expect(colorKeyOf([NOTES, STATUS, fuel], null)).toBeNull();
});
it('should not color the map by an archived key', () => {
  expect(colorKeyOf([{ ...STATUS, archived: true }])).toBeNull();
});
it('should not change the map data it receives', () => {
  withTags(mapData, [STATUS], []);
  expect(mapData.keys).toBeUndefined();
  expect(mapData.features[0].properties.point_tags).toBeUndefined();
});

// colorKeys
it('should color the map only by keys with one value from a list, not archived', () => {
  const archived = { ...STATUS, id: "k-old", archived: true };
  const many = { ...STATUS, id: "k-many", single: false };

  expect(colorKeys([STATUS, NOTES, archived, many]).map((key) => key.id)).toEqual(["k-status"]);
});

// expiresAt, shownValue (open, confirmed at 11:00, lasts 4 hours)
const point = (tags) => ({ point_tags: tags });

it('should expire a value the hours it lasts after it was last confirmed', () => {
  expect(expiresAt(OPEN, "2026-10-19T11:00:00Z").toISOString()).toEqual("2026-10-19T15:00:00.000Z");
  expect(expiresAt(CLOSED, "2026-10-19T11:00:00Z")).toBeNull();
});
it('should show the value while it lasts and unknown once it expired', () => {
  expect(shownValue(point([tag(OPEN.id)]), STATUS, at("14:59"))).toEqual(OPEN.id);
  expect(shownValue(point([tag(OPEN.id)]), STATUS, at("15:00"))).toEqual(UNKNOWN);
});
it('should always show a value that does not expire', () => {
  expect(shownValue(point([tag(CLOSED.id)]), STATUS, at("23:59"))).toEqual(CLOSED.id);
});
it('should show nothing without a value, a key, or a value the key does not have', () => {
  expect(shownValue(point([]), STATUS, at("12:00"))).toBeNull();
  expect(shownValue(point([tag(OPEN.id)]), null, at("12:00"))).toBeNull();
  expect(shownValue(point([tag("v-other")]), STATUS, at("12:00"))).toBeNull();
});

// withShownValues
it('should tell what each point shows now for the key, as color_value', () => {
  const data = { features: [{ properties: { id: "p-1", point_tags: [tag(OPEN.id)] } }, { properties: { id: "p-2" } }] };
  const [first, second] = withShownValues(data, STATUS, at("16:00")).features;

  expect(first.properties.color_value).toEqual(UNKNOWN);
  expect(second.properties.color_value).toBeNull();
  expect(data.features[0].properties.color_value).toBeUndefined();
});

// keyFilter, keyFilterOf, shownValueCounts
it('should tell a filter by a value of a key from a filter by a free tag', () => {
  expect(keyFilterOf(keyFilter("k-status", OPEN.id))).toEqual({ keyId: "k-status", valueId: OPEN.id });
  expect(keyFilterOf("guard")).toBeNull();
  expect(keyFilterOf(undefined)).toBeNull();
});
it('should count the points that show each value now, expired ones as unknown', () => {
  const features = [
    { properties: { point_tags: [tag(OPEN.id)] } },
    { properties: { point_tags: [tag(OPEN.id, "06:00")] } },
    { properties: { point_tags: [tag(CLOSED.id)], removed: true } },
    { properties: { point_tags: [] } },
  ];

  expect(shownValueCounts(features, STATUS, at("12:00"))).toEqual([
    { id: OPEN.id, value: "Open", color: "#3E9E47", count: 1 },
    { id: CLOSED.id, value: "Closed", color: "#D73F3F", count: 0 },
    { id: UNKNOWN, value: null, color: null, count: 1 },
  ]);
});

// valuesInUse
it('should tell the values some point has', () => {
  const features = [{ properties: { point_tags: [tag(OPEN.id), { key_id: NOTES.id, value_id: null, value: "x" }] } }];

  expect([...valuesInUse(features)]).toEqual([OPEN.id]);
});

// textOn
it('should write white over dark colors and dark over light ones', () => {
  expect(textOn("#D73F3F")).toEqual("#FFFFFF");
  expect(textOn("#E9A23B")).toEqual("#1F2329");
  expect(textOn(undefined)).toEqual("#FFFFFF");
});

// freeTags, freeTagsInUse
it('should split the free tags of a point and count them, the most used first', () => {
  expect(freeTags("guard,,pediatrics")).toEqual(["guard", "pediatrics"]);
  expect(freeTagsInUse([
    { properties: { tags: "guard,pediatrics" } },
    { properties: { tags: "guard" } },
    { properties: { tags: "control", removed: true } },
  ])).toEqual([{ tag: "guard", count: 2 }, { tag: "pediatrics", count: 1 }]);
});

// newPoint
it('should make a point added by hand, as the API takes it and as the map shows it', () => {
  const { request, feature } = newPoint({ id: "p-9", name: "South access", coordinates: [35.2, 31.9], time: "2026-10-13T12:00:00.000Z" });

  expect(request).toEqual({ id: "p-9", longitude: 35.2, latitude: 31.9, time: "2026-10-13T12:00:00.000Z", message: "South access" });
  expect(feature.geometry.coordinates).toEqual([35.2, 31.9]);
  expect(feature.properties.point_tags).toEqual([]);
});

// keysOn, usesKeys
it('should show the keys of a map only with the dashboard parameter', () => {
  expect(keysOn("#/map/map-1?dashboard")).toBe(true);
  expect(keysOn("#/map/map-1?other=1&dashboard")).toBe(true);
  expect(keysOn("#/map/map-1")).toBe(false);
  expect(keysOn("#/map/map-1?dash")).toBe(false);
});

it('should tell a map read with its keys, even none, from one read without them', () => {
  expect(usesKeys({ keys: [] })).toBe(true);
  expect(usesKeys({ features: [] })).toBe(false);
  expect(usesKeys(null)).toBe(false);
});

// withKeyTags
it('should replace what a point has for a key with what the API answers, keeping its other keys', () => {
  const properties = { id: "p-1", point_tags: [
    { key_id: "k-status", value_id: "v-open" }, { key_id: "k-notes", value: "Gate" },
  ]};
  const changed = withKeyTags(properties, "k-status", [{ key_id: "k-status", value_id: "v-closed" }]);

  expect(changed.point_tags).toEqual([{ key_id: "k-notes", value: "Gate" }, { key_id: "k-status", value_id: "v-closed" }]);
  expect(properties.point_tags[0].value_id).toBe("v-open");
});
