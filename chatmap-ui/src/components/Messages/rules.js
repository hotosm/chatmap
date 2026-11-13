// The rules of a map over the messages of its groups, as the editor writes them (see the API v2 rules)

export const CONTENT = "content";
export const GROUP = "group";
export const CONTAINS = "contains";
export const NOT_CONTAINS = "not_contains";
export const IS = "is";
export const IS_NOT = "is_not";
// When a message was sent, in the time zone the rule is written in: the time of day, from-to, and the day of the week
export const TIME = "time";
export const WEEKDAY = "weekday";
export const BETWEEN = "between";
export const WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
export const HIGHLIGHT = "highlight";
export const SUGGEST_PLACE = "suggest_place";
export const SUGGEST_STATUS = "suggest_status";
export const HIDE = "hide";
// The actions, in the order the editor shows them
export const ACTIONS = [HIGHLIGHT, SUGGEST_PLACE, SUGGEST_STATUS, HIDE];
// What a condition can say: of a field, its operators
export const KINDS = [
    { field: CONTENT, operator: CONTAINS },
    { field: CONTENT, operator: NOT_CONTAINS },
    { field: GROUP, operator: IS },
    { field: GROUP, operator: IS_NOT },
    { field: TIME, operator: BETWEEN },
    { field: WEEKDAY, operator: IS },
];
// As the API takes them
export const MAX_DESCRIPTION_LENGTH = 100;
export const MAX_CONDITION_LENGTH = 100;
export const MAX_CONDITIONS = 10;
export const MAX_RULE_CONDITIONS = 20;
export const MAX_CONDITION_VALUES = 10;

// The time zone of whoever writes the rule, as the browser tells it
export const localZone = () => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

// A condition to start writing: a time of day starts as a morning, the days of the week to choose
export const newCondition = (field = CONTENT, operator = CONTAINS) =>
    field === TIME ? { field, operator, values: ["08:00", "12:00"], timezone: localZone() } :
    field === WEEKDAY ? { field, operator, values: [], timezone: localZone() } :
    { field, operator, values: [] };

// Whether a condition says all it needs: a value, and two different times for a time of day
export const isComplete = (condition) => condition.field === TIME ?
    condition.values.length === 2 && condition.values.every(Boolean) && condition.values[0] !== condition.values[1] :
    condition.values.length > 0;
export const newGroup = (match = "any") => ({ match, items: [newCondition()] });
export const isGroup = (item) => Array.isArray(item.items);

// A rule to start writing: all of one condition on what the message says
export const newRule = () => ({
    description: "",
    enabled: true,
    conditions: newGroup("all"),
    actions: [],
});

// Every condition of a group, inside its groups too
export const conditionsOf = (group) =>
    group.items.flatMap((item) => isGroup(item) ? conditionsOf(item) : [item]);

// The group with its item at index changed by change(item), or taken out when it gives null
export const withItem = (group, index, change) => ({
    ...group,
    items: group.items.flatMap((item, i) => {
        if (i !== index) return [item];
        const changed = change(item);
        return changed ? [changed] : [];
    }),
});

// A value added to a condition, trimmed and once, while there is room for it
export const withValue = (condition, value, max = MAX_CONDITION_VALUES) => {
    const added = value.trim();
    if (!added || condition.values.includes(added) || condition.values.length >= max) return condition;
    return { ...condition, values: [...condition.values, added] };
};

export const actionOf = (rule, type) => rule.actions.find((action) => action.type === type) || null;

/**
 * The rule with an action on or off. Hiding goes alone: turning it on takes
 * the others out, and turning another on takes hiding out.
 */
export const withAction = (rule, type, on) => {
    const others = rule.actions.filter((action) => action.type !== type);
    if (!on) return { ...rule, actions: others };
    const kept = type === HIDE ? [] : others.filter((action) => action.type !== HIDE);
    return { ...rule, actions: [...kept, { type }] };
};

// The rule with an action changed: { point_id } for a place, { key_id, value_id } for a status
export const withActionValue = (rule, type, values) => ({
    ...rule,
    actions: rule.actions.map((action) => action.type === type ? { ...action, ...values } : action),
});

// The actions that take conditions of their own: the suggestions
export const SUGGESTIONS = [SUGGEST_PLACE, SUGGEST_STATUS];

/**
 * The texts an action looks for, of its own: a suggestion is made only when
 * the message says any of them. The editor writes them as one condition.
 */
export const actionWords = (action) =>
    action && action.conditions ? conditionsOf(action.conditions).flatMap((condition) => condition.values) : [];

// The action with the texts it looks for; none takes its conditions out
export const withActionWords = (rule, type, values) => ({
    ...rule,
    actions: rule.actions.map((action) => {
        if (action.type !== type) return action;
        const { conditions, ...rest } = action;
        return values.length ? { ...rest, conditions: { match: "any", items: [{ field: CONTENT, operator: CONTAINS, values }] } } : rest;
    }),
});

// The texts an action looks for to start from: the name of the place or the status it suggests, when it has none yet
export const withNameToLookFor = (rule, type, name) =>
    name && actionWords(actionOf(rule, type)).length === 0 ?
        withActionWords(rule, type, [name.trim().slice(0, MAX_CONDITION_LENGTH)]) :
        rule;

/**
 * What keeps a rule from being saved, as the API checks it, or none:
 * "description", "condition" (one without values, or a group without
 * conditions), "noCondition" (none in the rule nor in its suggestions),
 * "tooMany" (conditions), "action" (none), "place" or
 * "status" (suggested without choosing one), "highlight" (it needs a
 * condition on a text the message contains).
 */
export const ruleProblems = (rule) => {
    const problems = [];
    const own = conditionsOf(rule.conditions);
    const words = rule.actions.flatMap(actionWords);
    const conditions = [...own, ...words.length ? [{ operator: CONTAINS, values: words }] : []];
    const empty = (group) => group.items.some((item) => isGroup(item) && (item.items.length === 0 || empty(item)));
    if (!rule.description.trim()) problems.push("description");
    if (empty(rule.conditions) || own.some((condition) => !isComplete(condition))) problems.push("condition");
    if (own.length === 0 && words.length === 0) problems.push("noCondition");
    if (own.length + rule.actions.filter((action) => actionWords(action).length).length > MAX_RULE_CONDITIONS) {
        problems.push("tooMany");
    }
    if (rule.actions.length === 0) problems.push("action");
    const place = actionOf(rule, SUGGEST_PLACE);
    if (place && !place.point_id) problems.push("place");
    const status = actionOf(rule, SUGGEST_STATUS);
    if (status && !(status.key_id && status.value_id)) problems.push("status");
    if (actionOf(rule, HIGHLIGHT) && !conditions.some((condition) => condition.operator === CONTAINS)) {
        problems.push("highlight");
    }
    return problems;
};

const groupToSend = (group) => ({
    match: group.match,
    items: group.items.map((item) => isGroup(item) ?
        groupToSend(item) :
        {
            field: item.field, operator: item.operator, values: item.values.map((value) => value.trim()),
            ...(item.field === TIME || item.field === WEEKDAY ? { timezone: item.timezone || localZone() } : {}),
        }
    ),
});

// A rule as the API takes it: what it says, without its id
export const toSend = (rule) => ({
    description: rule.description.trim(),
    enabled: rule.enabled,
    conditions: groupToSend(rule.conditions),
    actions: rule.actions.map(({ type, point_id, key_id, value_id, conditions }) =>
        Object.fromEntries(Object.entries({
            type, point_id, key_id, value_id,
            conditions: conditions && conditionsOf(conditions).length ? groupToSend(conditions) : null,
        }).filter(([, value]) => value))
    ),
});

// A copy of a rule to save as a new one, off until its owner turns it on
export const copyOf = (rule, suffix) => ({
    ...toSend(rule),
    description: `${rule.description} ${suffix}`.slice(0, MAX_DESCRIPTION_LENGTH),
    enabled: false,
});


const words = (text) => text.split(",").map((word) => word.trim()).filter((word) => word);

const lookingFor = (type, said) =>
    ({ type, conditions: { match: "any", items: [{ field: CONTENT, operator: CONTAINS, values: words(said) }] } });

/**
 * Rules to start from, written with the words of the language of the page
 * (comma-separated texts): a place that closes, what a group says, and the
 * noise to hide. Each suggestion is made when the message says what it
 * looks for. The place, the status and the group are left for its owner.
 *
 * @param {object} said { place, closed, open, greetings, ...descriptions } as texts
 */
export const ruleExamples = (said) => [
    {
        id: "closed",
        rule: {
            ...newRule(),
            description: said.closedPlace,
            conditions: { match: "all", items: [{ field: CONTENT, operator: NOT_CONTAINS, values: words(said.open) }] },
            actions: [{ type: HIGHLIGHT }, lookingFor(SUGGEST_PLACE, said.place), lookingFor(SUGGEST_STATUS, said.closed)],
        },
    },
    {
        id: "group",
        rule: {
            ...newRule(),
            description: said.fromGroup,
            conditions: { match: "all", items: [{ field: GROUP, operator: IS, values: [] }] },
            actions: [{ type: HIGHLIGHT }, { type: SUGGEST_PLACE }, lookingFor(SUGGEST_STATUS, said.closed)],
        },
    },
    {
        id: "greetings",
        rule: {
            ...newRule(),
            description: said.hideGreetings,
            conditions: { match: "any", items: [{ field: CONTENT, operator: CONTAINS, values: words(said.greetings) }] },
            actions: [{ type: HIDE }],
        },
    },
];

/**
 * Why a rule would take far more messages than it seems to look for, or
 * null: with "any", a condition on a group takes every message of that
 * group ("group"), one on when it was sent every message sent then
 * ("time"), and one that says what a text must not have takes almost every
 * message ("negation"). Usually "all" was meant.
 */
export const tooBroad = (rule) => {
    if (rule.conditions.match !== "any" || rule.conditions.items.length < 2) return null;
    const items = rule.conditions.items.filter((item) => !isGroup(item));
    if (items.some((item) => item.operator === NOT_CONTAINS || item.operator === IS_NOT)) return "negation";
    if (items.some((item) => item.field === GROUP)) return "group";
    if (items.some((item) => item.field === TIME || item.field === WEEKDAY)) return "time";
    return null;
};
