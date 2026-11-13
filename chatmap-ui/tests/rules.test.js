import { expect, test as it } from 'vitest'

import {
  BETWEEN, CONTAINS, HIDE, HIGHLIGHT, IS, MAX_CONDITION_VALUES, NOT_CONTAINS, TIME, WEEKDAY, tooBroad, SUGGEST_PLACE, SUGGEST_STATUS, actionOf, actionWords, conditionsOf,
  copyOf, newCondition, newGroup, newRule, ruleProblems, toSend, withAction, withActionValue, withActionWords, withItem,
  withNameToLookFor, withValue,
} from '../src/components/Messages/rules';

const contains = (...values) => ({ field: "content", operator: CONTAINS, values });
const rule = (changes = {}) => ({ ...newRule(), description: "North closed", ...changes });
const types = (item) => item.actions.map((action) => action.type);

// withAction, withActionValue
it('turns actions on and off, and hiding goes alone', () => {
  const both = withAction(withAction(rule(), HIGHLIGHT, true), SUGGEST_PLACE, true);
  expect(types(both)).toEqual([HIGHLIGHT, SUGGEST_PLACE]);
  expect(types(withAction(both, HIGHLIGHT, false))).toEqual([SUGGEST_PLACE]);

  const hidden = withAction(both, HIDE, true);
  expect(types(hidden)).toEqual([HIDE]);
  expect(types(withAction(hidden, SUGGEST_STATUS, true))).toEqual([SUGGEST_STATUS]);
});

// withActionWords, withNameToLookFor
it('gives a suggestion texts of its own to look for, starting from the name it suggests', () => {
  const place = withAction(rule(), SUGGEST_PLACE, true);
  const named = withNameToLookFor(withActionValue(place, SUGGEST_PLACE, { point_id: "p-1" }), SUGGEST_PLACE, " Puente Norte ");
  expect(actionWords(actionOf(named, SUGGEST_PLACE))).toEqual(["Puente Norte"]);
  // What it already looks for stays when another place is chosen
  const other = withNameToLookFor(withActionValue(named, SUGGEST_PLACE, { point_id: "p-2" }), SUGGEST_PLACE, "Puente Sur");
  expect(actionOf(other, SUGGEST_PLACE)).toEqual({ ...actionOf(named, SUGGEST_PLACE), point_id: "p-2" });
  // Without texts, it takes its conditions out
  expect(actionOf(withActionWords(other, SUGGEST_PLACE, []), SUGGEST_PLACE)).toEqual({ type: SUGGEST_PLACE, point_id: "p-2" });
});

// withValue, withItem, conditionsOf
it('adds a value to a condition trimmed and once', () => {
  const condition = withValue(withValue(contains(), " cerrado "), "cerrado");
  expect(condition.values).toEqual(["cerrado"]);
  expect(withValue(condition, "  ").values).toEqual(["cerrado"]);
});

it('changes or takes out an item of a group, and finds the conditions inside its groups', () => {
  const group = { match: "all", items: [contains("a"), { match: "any", items: [contains("b"), contains("c")] }] };
  const changed = withItem(group, 1, (inner) => withItem(inner, 0, () => null));
  expect(changed.items[1].items).toEqual([contains("c")]);
  expect(withItem(group, 0, () => contains("z")).items[0]).toEqual(contains("z"));
  expect(conditionsOf(group).map((condition) => condition.values[0])).toEqual(["a", "b", "c"]);
});

// ruleProblems
it('tells what keeps a rule from being saved, as the API checks it', () => {
  expect(ruleProblems(newRule())).toEqual(["description", "condition", "action"]);

  const ready = withAction(rule({ conditions: { match: "all", items: [contains("cerrado")] } }), HIGHLIGHT, true);
  expect(ruleProblems(ready)).toEqual([]);

  const negated = { ...ready, conditions: { match: "all", items: [{ ...contains("ya"), operator: NOT_CONTAINS }] } };
  expect(ruleProblems(negated)).toEqual(["highlight"]);

  const emptyGroup = { ...ready, conditions: { match: "all", items: [contains("a"), { match: "any", items: [] }] } };
  expect(ruleProblems(emptyGroup)).toEqual(["condition"]);

  const many = { ...ready, conditions: { match: "all", items: Array.from({ length: 3 }, () => ({ match: "any", items: Array.from({ length: 8 }, () => contains("x")) })) } };
  expect(ruleProblems(many)).toEqual(["tooMany"]);

  const unchosen = withAction(withAction(ready, SUGGEST_PLACE, true), SUGGEST_STATUS, true);
  expect(ruleProblems(unchosen)).toEqual(["place", "status"]);

  // The conditions can be only the ones of its suggestions, which also give what to highlight; but some there must be
  const bare = withActionValue({ ...unchosen, conditions: { match: "all", items: [] } }, SUGGEST_PLACE, { point_id: "p-1" });
  const all = withActionValue(bare, SUGGEST_STATUS, { key_id: "k-1", value_id: "v-1" });
  expect(ruleProblems(all)).toEqual(["noCondition", "highlight"]);
  expect(ruleProblems(withActionWords(all, SUGGEST_PLACE, ["puente"]))).toEqual([]);
});

// toSend, copyOf
it('sends a rule trimmed, its groups too, with only what each action needs', () => {
  const written = {
    id: "r-1", position: 3, description: " North ", enabled: true,
    conditions: { match: "all", items: [contains(" cerrado "), { ...newGroup(), items: [{ field: "group", operator: IS, values: ["g-1"] }] }] },
    actions: [{ type: SUGGEST_STATUS, key_id: "k-1", value_id: "v-1", point_id: null }],
  };
  expect(toSend(written)).toEqual({
    description: "North", enabled: true,
    conditions: { match: "all", items: [contains("cerrado"), { match: "any", items: [{ field: "group", operator: IS, values: ["g-1"] }] }] },
    actions: [{ type: SUGGEST_STATUS, key_id: "k-1", value_id: "v-1" }],
  });

  const looking = withActionWords({ ...written, actions: [{ type: SUGGEST_PLACE, point_id: "p-1" }] }, SUGGEST_PLACE, [" puente "]);
  expect(toSend(looking).actions).toEqual([
    { type: SUGGEST_PLACE, point_id: "p-1", conditions: { match: "any", items: [contains("puente")] } },
  ]);
});

it('copies a rule off, with its name and a suffix within the length the API takes', () => {
  const copy = copyOf(rule({ description: "x".repeat(98) }), "(copy)");
  expect(copy.enabled).toBe(false);
  expect(copy.description).toHaveLength(100);
  expect(copyOf(rule(), "(copia)").description).toBe("North closed (copia)");
});

// tooBroad
it('warns when "any" would take every message of a group, or almost every message', () => {
  const group = { field: "group", operator: IS, values: ["g-1"] };
  const negated = { ...contains("abrieron"), operator: NOT_CONTAINS };
  const rule = (match, ...items) => ({ ...newRule(), conditions: { match, items } });
  expect(tooBroad(rule("any", contains("abierto"), group))).toBe("group");
  expect(tooBroad(rule("any", contains("cerrado"), negated))).toBe("negation");
  expect(tooBroad(rule("all", contains("abierto"), group))).toBeNull();
  expect(tooBroad(rule("any", contains("abierto"), contains("libre")))).toBeNull();
  expect(tooBroad(rule("any", group))).toBeNull();
});

it("adds values up to the room a list has, the one of a condition by default", () => {
  const condition = { field: "content", operator: "contains", values: ["a", "b"] };
  expect(withValue(condition, "c", 2).values).toEqual(["a", "b"]);
  expect(withValue(condition, "c", 3).values).toEqual(["a", "b", "c"]);
  const full = { ...condition, values: Array.from({ length: MAX_CONDITION_VALUES }, (_, i) => `w${i}`) };
  expect(withValue(full, "more").values).toHaveLength(MAX_CONDITION_VALUES);
});

// When a message was sent
it('takes a time of day only with two different times, and the zone of whoever writes it', () => {
  const rule = (condition) => ({ description: "Nights", enabled: true, conditions: { match: "all", items: [condition] }, actions: [{ type: "hide" }] });
  const night = { ...newCondition(TIME, BETWEEN), values: ["22:00", "06:00"], timezone: "America/Argentina/Buenos_Aires" };
  expect(ruleProblems(rule(night))).toEqual([]);
  expect(ruleProblems(rule({ ...night, values: ["22:00", "22:00"] }))).toContain("condition");
  expect(ruleProblems(rule(newCondition(WEEKDAY, IS)))).toContain("condition");
  expect(toSend(rule(night)).conditions.items[0]).toEqual({ field: TIME, operator: BETWEEN, values: ["22:00", "06:00"], timezone: "America/Argentina/Buenos_Aires" });
  // With "any", every message sent then would meet it
  expect(tooBroad({ ...rule(night), conditions: { match: "any", items: [night, newCondition()] } })).toBe("time");
});
