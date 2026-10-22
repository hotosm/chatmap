import { beforeEach, expect, test as it, vi } from 'vitest'

import { tagsPaint } from '../src/components/Tags/mapLayer';
import { mapTags } from '../src/components/Tags/useMapTags';
import { keyFilter, UNKNOWN } from '../src/components/Tags/tags';

const NOW = new Date("2026-10-06T12:00:00Z").getTime();

// Keys are on, as with ?dashboard in the address
beforeEach(() => vi.stubGlobal('window', { location: { hash: '#/map/map-1?dashboard' } }));

const POINT_COLOR = '#2E4873';
const KEY = { id: "k-1", values: [{ id: "v-1", color: "#3E9E47" }, { id: "v-2", color: null }] };
const SHOWN = ["coalesce", ["get", "color_value"], ""];

it('should leave the points as they are without a key that colors the map', () => {
  expect(tagsPaint(null, POINT_COLOR)).toEqual({ 'circle-color': POINT_COLOR, 'circle-stroke-width': 0 });
  expect(tagsPaint({ id: "k-1", values: [] }, POINT_COLOR)['circle-color']).toBe(POINT_COLOR);
});

it('should fill each point with the color of the value it shows now, gray when the value has none', () => {
  const [, hasValue, byValue, fallback] = tagsPaint(KEY, POINT_COLOR)['circle-color'];

  expect(byValue[1]).toEqual(SHOWN);
  expect(byValue.slice(2, 6)).toEqual(["v-1", "#3E9E47", "v-2", "#9A969B"]);
  expect(hasValue[2][2][1]).toContain(UNKNOWN);
  expect(fallback).toBe(POINT_COLOR);
});

it('should outline the points with a value, an expired one in gray', () => {
  const paint = tagsPaint(KEY, POINT_COLOR);

  expect(paint['circle-stroke-width'].slice(2)).toEqual([3, 0]);
  expect(paint['circle-stroke-color']).toEqual(["match", SHOWN, UNKNOWN, '#9A969B', '#FFFFFF']);
});

// mapTags
const DATA = { features: [
  { properties: { id: "p-1", point_tags: [{ key_id: "k-1", value_id: "v-1" }] } },
  { properties: { id: "p-2", point_tags: [] } },
]};

it('should leave a map read without its keys as it always was', () => {
  const tags = mapTags(DATA, NOW);

  expect(tags.colorKey).toBeNull();
  expect(tags.shown(DATA)).toBe(DATA);
  expect(tags.filter(keyFilter("k-1", "v-1"))).toBeNull();
});

it('should show and filter by the values of the key that colors the map', () => {
  const data = { ...DATA, keys: [{ ...KEY, single: true, closed: true, colors_map: true }] };
  const tags = mapTags(data, NOW);
  const byValue = tags.filter(keyFilter("k-1", "v-1"));

  expect(tags.colorKey.id).toBe("k-1");
  expect(tags.shown(data).features.map((feature) => feature.properties.color_value)).toEqual(["v-1", null]);
  expect(data.features.filter(byValue).map((feature) => feature.properties.id)).toEqual(["p-1"]);
  expect(tags.filter("some free tag")).toBeNull();
});

it('should leave the map as it always was when keys are turned off, even if it was read with them', () => {
  vi.stubGlobal('window', { location: { hash: '#/map/map-1' } });
  const data = { ...DATA, keys: [{ ...KEY, single: true, closed: true, colors_map: true }] };

  expect(mapTags(data, NOW).shown(data)).toBe(data);
});
