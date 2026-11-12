import { useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlIconButton from "@shoelace-style/shoelace/dist/react/icon-button/index.js";

import {
    CONTENT, GROUP, KINDS, MAX_CONDITION_LENGTH, MAX_CONDITION_VALUES, MAX_CONDITIONS, isGroup, newCondition,
    newGroup, withItem, withValue,
} from "./rules.js";
import useGroupName from "./useGroupName.js";

const KIND_NAMES = {
    "content:contains": ["app.rules.contains", "The text contains any of"],
    "content:not_contains": ["app.rules.notContains", "The text contains none of"],
    "group:is": ["app.rules.groupIs", "The group is one of"],
    "group:is_not": ["app.rules.groupIsNot", "The group is none of"],
};

// A native select drawn as a pill (styles/controls.css)
export function PillSelect({ value, onChange, children, label }) {
    return (
        <span className="pill pill--outline pill--caret">
            <select className="pill__select" value={value} aria-label={label} onChange={(event) => onChange(event.target.value)}>
                {children}
            </select>
        </span>
    );
}

/**
 * The values of a condition as pills, each one to take out; a text is added
 * on Enter or with a comma. Up to max values of up to maxLength characters:
 * the ones of a condition, by default. placeholder: what the field says
 * while empty, instead of the example of a condition.
 */
export function Values({
    condition, groups, onChange, max = MAX_CONDITION_VALUES, maxLength = MAX_CONDITION_LENGTH, placeholder = null,
}) {
    const intl = useIntl();
    const groupName = useGroupName();
    const [text, setText] = useState("");
    const full = condition.values.length >= max;
    const name = (value) => condition.field === GROUP ?
        groupName((groups.find((group) => group.id === value) || {}).name) : value;

    const add = (value) => {
        onChange(withValue(condition, value, max));
        setText("");
    };
    const handleKeyDown = (event) => {
        if ((event.key === "Enter" || event.key === ",") && text.trim()) {
            event.preventDefault();
            add(text);
        } else if (event.key === "Backspace" && !text && condition.values.length > 0) {
            onChange({ ...condition, values: condition.values.slice(0, -1) });
        }
    };

    return (
        <div className="ruleValues">
            { condition.values.map((value) =>
                <span key={value} className="pill pill--outline ruleValues__value">
                    <bdi>{name(value)}</bdi>
                    <button
                        type="button"
                        className="pointTags__remove"
                        aria-label={intl.formatMessage({ id: "app.tags.remove", defaultMessage: "Remove {tag}" }, { tag: name(value) })}
                        onClick={() => onChange({ ...condition, values: condition.values.filter((item) => item !== value) })}
                    >
                        ×
                    </button>
                </span>
            )}
            { !full && condition.field === CONTENT &&
                <input
                    className="ruleValues__input"
                    dir="auto"
                    value={text}
                    maxLength={maxLength}
                    placeholder={condition.values.length ?
                        intl.formatMessage({ id: "app.rules.addValue", defaultMessage: "Another one…" }) :
                        placeholder || intl.formatMessage({ id: "app.rules.writeValue", defaultMessage: "Write and press Enter" })
                    }
                    onChange={(event) => setText(event.target.value)}
                    onKeyDown={handleKeyDown}
                    // What was written and not added yet goes in when the field is left
                    onBlur={() => text.trim() && add(text)}
                />
            }
            { !full && condition.field === GROUP &&
                <PillSelect
                    value=""
                    label={intl.formatMessage({ id: "app.rules.group", defaultMessage: "Group" })}
                    onChange={(value) => value && add(value)}
                >
                    <option value="">{intl.formatMessage({ id: "app.rules.chooseGroup", defaultMessage: "Choose a group" })}</option>
                    { groups.filter((group) => !condition.values.includes(group.id)).map((group) =>
                        <option key={group.id} value={group.id}>{groupName(group.name)}</option>
                    )}
                </PillSelect>
            }
        </div>
    );
}

/**
 * Conditions that go together, all of them or any: each one with what it
 * looks at and its values, or a group of its own one level down. A rule's
 * conditions are a group (top); only that one can hold groups, and be left
 * without conditions, when its suggestions say when they are made.
 *
 * @param {object} group { match, items }
 * @param {array} groups The chat groups the map listens to, for the conditions on them
 * @param {function} onChange Gets the group changed
 * @param {function} onRemove Takes the group out; none for the group of the rule
 */
export default function ConditionGroup({ group, groups, top, onChange, onRemove }) {
    const intl = useIntl();
    const text = (id, defaultMessage) => intl.formatMessage({ id, defaultMessage });
    const full = group.items.length >= MAX_CONDITIONS;
    const set = (index, change) => onChange(withItem(group, index, change));

    return (
        <div className={top ? "conditionGroup" : "conditionGroup conditionGroup--inner"}>
            { group.items.length > 0 &&
                <p className="ruleForm__line">
                    { top ?
                        <FormattedMessage id="app.rules.if" defaultMessage="If the message meets" /> :
                        <FormattedMessage id="app.rules.groupOf" defaultMessage="Group: it meets" />
                    }
                    <PillSelect value={group.match} label={text("app.rules.match", "How many conditions")} onChange={(match) => onChange({ ...group, match })}>
                        <option value="all">{text("app.rules.all", "all")}</option>
                        <option value="any">{text("app.rules.any", "any")}</option>
                    </PillSelect>
                    <FormattedMessage id="app.rules.ofThese" defaultMessage="of these conditions:" />
                    { onRemove &&
                        <SlIconButton className="conditionGroup__remove" name="x-lg" label={text("app.rules.removeGroup", "Take out this group")} onClick={onRemove} />
                    }
                </p>
            }

            { group.items.length === 0 &&
                <p className="messageLinker__notice">
                    <FormattedMessage
                        id="app.rules.noConditions"
                        defaultMessage="No conditions for the whole rule: each suggestion is made when the message says what it looks for."
                    />
                </p>
            }
            <ul className="conditionGroup__items">
                { group.items.map((item, index) =>
                    <li key={index} className="conditionGroup__item">
                        { isGroup(item) ?
                            <ConditionGroup
                                group={item}
                                groups={groups}
                                onChange={(changed) => set(index, () => changed)}
                                onRemove={() => set(index, () => null)}
                            /> :
                            <div className="ruleForm__condition">
                                <PillSelect
                                    value={`${item.field}:${item.operator}`}
                                    label={text("app.rules.conditionField", "What it looks at")}
                                    onChange={(kind) => {
                                        const [field, operator] = kind.split(":");
                                        // The values of a text are not groups, nor the other way round
                                        set(index, (condition) => ({ field, operator, values: field === condition.field ? condition.values : [] }));
                                    }}
                                >
                                    { KINDS.map(({ field, operator }) =>
                                        <option key={`${field}:${operator}`} value={`${field}:${operator}`} disabled={field === GROUP && groups.length === 0}>
                                            {text(...KIND_NAMES[`${field}:${operator}`])}
                                        </option>
                                    )}
                                </PillSelect>
                                <Values condition={item} groups={groups} onChange={(changed) => set(index, () => changed)} />
                                { (top || group.items.length > 1) &&
                                    <SlIconButton name="x-lg" label={text("app.rules.removeCondition", "Take out this condition")} onClick={() => set(index, () => null)} />
                                }
                            </div>
                        }
                    </li>
                )}
            </ul>

            { !full &&
                <div className="conditionGroup__add">
                    <button type="button" className="messageLinks__undo" onClick={() => onChange({ ...group, items: [...group.items, newCondition()] })}>
                        <FormattedMessage id="app.rules.addCondition" defaultMessage="Add a condition" />
                    </button>
                    { top &&
                        <button type="button" className="messageLinks__undo" onClick={() => onChange({ ...group, items: [...group.items, newGroup()] })}>
                            <FormattedMessage id="app.rules.addGroup" defaultMessage="Add a group of conditions" />
                        </button>
                    }
                </div>
            }
        </div>
    );
}
