import { useMemo, useRef, useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";

import { KeyValues, ValueChip } from "../Tags";
import ConditionGroup, { Values } from "./ConditionGroup.jsx";
import PlacePicker from "./PlacePicker.jsx";
import { placesOf } from "./messages.js";
import {
    ACTIONS, CONTENT, CONTAINS, HIDE, MAX_DESCRIPTION_LENGTH, MAX_RULE_CONDITIONS, SUGGESTIONS, SUGGEST_PLACE,
    SUGGEST_STATUS, actionOf, actionWords, ruleProblems, tooBroad, withAction, withActionValue, withActionWords,
    withNameToLookFor,
} from "./rules.js";

const ACTION_NAMES = {
    highlight: <FormattedMessage id="app.rules.highlight" defaultMessage="Highlight what matched" />,
    suggest_place: <FormattedMessage id="app.rules.suggestPlace" defaultMessage="Suggest place" />,
    suggest_status: <FormattedMessage id="app.rules.suggestStatus" defaultMessage="Suggest status" />,
    hide: <FormattedMessage id="app.rules.hide" defaultMessage="Hide (dismiss it)" />,
};

const MISSING = {
    description: ["app.rules.missingDescription", "what it is for"],
    condition: ["app.rules.missingCondition", "a value in each condition"],
    noCondition: ["app.rules.missingAnyCondition", "a condition, of the rule or of a suggestion"],
    action: ["app.rules.missingAction", "something to do"],
    place: ["app.rules.missingPlace", "the place"],
    status: ["app.rules.missingStatus", "the status"],
};

// What a suggestion looks for in the text, of its own: it is made only when the message says any of it
function LookingFor({ rule, type, onChange }) {
    return (
        <div className="ruleForm__when">
            <span className="ruleForm__whenLabel">
                <FormattedMessage id="app.rules.whenTextContains" defaultMessage="if the text contains any of" />
            </span>
            <Values
                condition={{ field: CONTENT, operator: CONTAINS, values: actionWords(actionOf(rule, type)) }}
                groups={[]}
                onChange={(condition) => onChange(withActionWords(rule, type, condition.values))}
            />
            { type === SUGGEST_PLACE && actionWords(actionOf(rule, type)).length > 0 &&
                <span className="ruleForm__whenHelp">
                    <FormattedMessage
                        id="app.rules.placeWhenHelp"
                        defaultMessage="When the message does not name it, this rule suggests nothing."
                    />
                </span>
            }
        </div>
    );
}

// The status a rule suggests: a pill that opens the values of the keys with a list
function StatusPicker({ keys, action, onPick }) {
    const dropdown = useRef();
    const key = keys.find((item) => item.key.id === action.key_id);
    const value = key && key.options.find((item) => item.id === action.value_id);

    return (
        <sl-dropdown ref={dropdown} placement="bottom-start" hoist>
            <button slot="trigger" type="button" className="pill pill--outline pill--caret">
                { value ? <ValueChip value={value} /> : <FormattedMessage id="app.messages.chooseStatus" defaultMessage="Choose status" /> }
            </button>
            <div className="popoverPanel messagePicker__panel">
                <KeyValues
                    keys={keys}
                    onPick={(keyId, change) => {
                        onPick({ key_id: keyId, value_id: change.value_id });
                        dropdown.current && dropdown.current.hide();
                    }}
                />
            </div>
        </sl-dropdown>
    );
}

/**
 * Writing a rule, in its card: its description, its conditions (what the
 * message says or not, the group it comes from or not, in groups of all or
 * any of them) and what it does. Each suggestion can look for texts of its
 * own: choosing the place or the status writes its name there to start
 * from. It can be saved once nothing keeps the API from taking it.
 *
 * @param {object} rule The rule as it is (newRule for a new one)
 * @param {array} groups The groups the map listens to: [{ id, name }]
 * @param {array} keys The keys with a list the rule can suggest a value of: [{ key, options }]
 * @param {function} onSave Gets the rule; answers what was saved, or null when the API did not take it
 */
export default function RuleForm({ rule: start, mapData, groups, keys, onSave, onCancel }) {
    const intl = useIntl();
    const [rule, setRule] = useState(start);
    const [busy, setBusy] = useState(false);
    const [failed, setFailed] = useState(false);
    const places = useMemo(() => placesOf(mapData.features, null), [mapData.features]);
    const problems = ruleProblems(rule);
    const text = (id, defaultMessage) => intl.formatMessage({ id, defaultMessage });

    const save = async (event) => {
        event.preventDefault();
        if (problems.length > 0) return;
        setBusy(true);
        const saved = await onSave(rule);
        setBusy(false);
        setFailed(!saved);
    };

    // What keeps it from being saved, said: "Missing: a description and a status"
    const missing = problems.filter((problem) => MISSING[problem]).map((problem) => text(...MISSING[problem]));

    const place = actionOf(rule, SUGGEST_PLACE);
    const status = actionOf(rule, SUGGEST_STATUS);
    const valueName = ({ key_id, value_id }) => {
        const key = keys.find((item) => item.key.id === key_id);
        const value = key && key.options.find((item) => item.id === value_id);
        return value ? value.value : "";
    };

    return (
        <form className="messageCard ruleForm" onSubmit={save}>
            <SlInput
                size="small"
                value={rule.description}
                maxlength={MAX_DESCRIPTION_LENGTH}
                autocomplete="off"
                label={text("app.rules.description", "What it is for")}
                placeholder={text("app.rules.descriptionExample", "North access closed")}
                onSlInput={(event) => setRule({ ...rule, description: event.target.value })}
            />

            <section className="ruleForm__section">
                <ConditionGroup
                    top
                    group={rule.conditions}
                    groups={groups}
                    onChange={(conditions) => setRule({ ...rule, conditions })}
                />
                { tooBroad(rule) === "group" &&
                    <p className="ruleCard__warning">
                        <FormattedMessage
                            id="app.rules.broadGroup"
                            defaultMessage="With “any”, every message of the group meets it, whatever it says. To ask for both, choose “all”."
                        />
                    </p>
                }
                { tooBroad(rule) === "negation" &&
                    <p className="ruleCard__warning">
                        <FormattedMessage
                            id="app.rules.broadNegation"
                            defaultMessage="With “any”, almost every message meets it: most do not say what it leaves out. Choose “all”."
                        />
                    </p>
                }
                { problems.includes("tooMany") &&
                    <p className="messageLinker__notice messageLinker__notice--error">
                        <FormattedMessage id="app.rules.tooMany" defaultMessage="A rule takes up to {max} conditions." values={{ max: MAX_RULE_CONDITIONS }} />
                    </p>
                }
            </section>

            <section className="ruleForm__section">
                <p className="ruleForm__line">
                    <FormattedMessage id="app.rules.then" defaultMessage="Then:" />
                </p>
                <div className="ruleForm__actions">
                    { ACTIONS.map((type) => {
                        const on = Boolean(actionOf(rule, type));
                        return (
                            <div key={type} className="ruleForm__action">
                                <button
                                    type="button"
                                    className={`pill ${on ? "pill--on" : "pill--outline"}`}
                                    aria-pressed={on}
                                    onClick={() => setRule(withAction(rule, type, !on))}
                                >
                                    {ACTION_NAMES[type]}
                                </button>
                                { type === SUGGEST_PLACE && place &&
                                    <PlacePicker
                                        places={places}
                                        place={places.find((item) => item.id === place.point_id) || null}
                                        onPick={(item) => setRule(withNameToLookFor(
                                            withActionValue(rule, SUGGEST_PLACE, { point_id: item.id }), SUGGEST_PLACE, item.name,
                                        ))}
                                    />
                                }
                                { type === SUGGEST_STATUS && status &&
                                    <StatusPicker
                                        keys={keys}
                                        action={status}
                                        onPick={(values) => setRule(withNameToLookFor(
                                            withActionValue(rule, SUGGEST_STATUS, values), SUGGEST_STATUS, valueName(values),
                                        ))}
                                    />
                                }
                                { SUGGESTIONS.includes(type) && on &&
                                    <LookingFor rule={rule} type={type} onChange={setRule} />
                                }
                            </div>
                        );
                    })}
                </div>
                { actionOf(rule, HIDE) &&
                    <p className="messageLinker__notice">
                        <FormattedMessage
                            id="app.rules.hideHelp"
                            defaultMessage="The messages it meets go to Dismissed, marked by this rule. They come back with a click."
                        />
                    </p>
                }
                { problems.includes("highlight") &&
                    <p className="messageLinker__notice">
                        <FormattedMessage id="app.rules.highlightNeedsText" defaultMessage="To highlight, a condition has to look for a text the message contains." />
                    </p>
                }
            </section>

            <footer className="ruleForm__footer">
                <button type="submit" className="pill pill--on" disabled={busy || problems.length > 0}>
                    <FormattedMessage id="app.rules.save" defaultMessage="Save rule" />
                </button>
                { missing.length > 0 &&
                    <span className="messageLinker__notice">
                        <FormattedMessage
                            id="app.rules.missing"
                            defaultMessage="Missing: {what}"
                            values={{ what: intl.formatList(missing, { type: "conjunction" }) }}
                        />
                    </span>
                }
                <button type="button" className="groupsPicker__cancel" onClick={onCancel}>
                    <FormattedMessage id="app.dialog.confirm.cancel" defaultMessage="Cancel" />
                </button>
                { failed &&
                    <span className="messageLinker__notice messageLinker__notice--error" role="alert">
                        <FormattedMessage id="app.messages.notSaved" defaultMessage="It could not be saved. Try again." />
                    </span>
                }
            </footer>
        </form>
    );
}
