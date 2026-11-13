import { Fragment, useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";
import SlIconButton from "@shoelace-style/shoelace/dist/react/icon-button/index.js";

import { ValueChip } from "../Tags";
import { dayName, zoneName } from "./ConditionGroup.jsx";
import { CONTENT, HIDE, HIGHLIGHT, SUGGEST_PLACE, SUGGEST_STATUS, TIME, WEEKDAY, actionWords, isGroup, tooBroad } from "./rules.js";
import useGroupName from "./useGroupName.js";

// What each condition looks at, and how
const FIELDS = {
    content: { icon: "chat-left-text", name: ["app.rules.fieldText", "Text"] },
    group: { icon: "people", name: ["app.rules.fieldGroup", "Group"] },
    time: { icon: "clock", name: ["app.rules.fieldTime", "Time"] },
    weekday: { icon: "calendar-range", name: ["app.rules.fieldWeekday", "Day"] },
};
const HOW = {
    "content:contains": ["app.rules.howContains", "contains any of"],
    "content:not_contains": ["app.rules.howNotContains", "contains none of"],
    "group:is": ["app.rules.howIs", "is one of"],
    "group:is_not": ["app.rules.howIsNot", "is none of"],
    "time:between": ["app.rules.howBetween", "between"],
    "weekday:is": ["app.rules.howOn", "is"],
};

// "OR" / "AND" in a row of its own between two conditions, over a hairline
function Joined({ match }) {
    return (
        <div className="ruleCard__join" role="presentation">
            <span>
                { match === "all" ?
                    <FormattedMessage id="app.rules.and" defaultMessage="and" /> :
                    <FormattedMessage id="app.rules.or" defaultMessage="or" />
                }
            </span>
        </div>
    );
}

/**
 * A rule as it reads: on top, whether it is on, its name and what can be
 * done with it; below, IF with one condition per row (its values as pills,
 * "and" or "or" between them, a group of them framed) and THEN with what it
 * does, one action per row with what it looks for of its own. IF does not
 * show when only its suggestions have conditions. It warns when it takes
 * far more messages than it seems to.
 *
 * @param {object} nameOf What its conditions and actions refer to: { group(id), place(id), value(keyId, valueId) }
 */
export default function RuleCard({ rule, nameOf, busy, onToggle, onEdit, onCopy, onRemove }) {
    const intl = useIntl();
    const groupName = useGroupName();
    const [removing, setRemoving] = useState(false);
    const text = (id, defaultMessage) => intl.formatMessage({ id, defaultMessage });
    const broad = tooBroad(rule);

    // A row with what it looks at, how, and its values, each in its column
    const condition = (item) =>
        <div className="ruleCard__condition">
            <span className="ruleCard__field">
                <SlIcon name={FIELDS[item.field].icon} />
                {text(...FIELDS[item.field].name)}
            </span>
            <span className="ruleCard__how">{text(...HOW[`${item.field}:${item.operator}`])}</span>
            <span className="ruleCard__values">
                { item.field === TIME ?
                    <>
                        <span className="pill pill--outline ruleCard__value">{item.values[0]}</span>
                        <FormattedMessage id="app.rules.timeAnd" defaultMessage="and" />
                        <span className="pill pill--outline ruleCard__value">{item.values[1]}</span>
                        <span className="ruleCard__how">
                            <FormattedMessage id="app.rules.zone" defaultMessage="{zone} time" values={{ zone: zoneName(item.timezone) }} />
                        </span>
                    </> :
                    item.values.map((value) =>
                        <span key={value} className="pill pill--outline ruleCard__value">
                            <bdi>
                                { item.field === CONTENT ? value :
                                    item.field === WEEKDAY ? dayName(value, intl.locale, true) : groupName(nameOf.group(value)) }
                            </bdi>
                        </span>
                    )
                }
            </span>
        </div>;

    const conditions = (group, framed) =>
        <div className={framed ? "ruleCard__conditions ruleCard__conditions--group" : "ruleCard__conditions"}>
            { framed &&
                <span className="ruleCard__groupOf">
                    { group.match === "all" ?
                        <FormattedMessage id="app.rules.groupAllOf" defaultMessage="All of" /> :
                        <FormattedMessage id="app.rules.groupAnyOf" defaultMessage="Any of" />
                    }
                </span>
            }
            { group.items.map((item, index) =>
                <Fragment key={index}>
                    { index > 0 && <Joined match={group.match} /> }
                    { isGroup(item) ? conditions(item, true) : condition(item) }
                </Fragment>
            )}
        </div>;

    // What an action looks for of its own, after it: "if the text contains any of [chips]"
    const lookingFor = (item) => {
        const words = actionWords(item);
        return words.length > 0 &&
            <>
                <span className="ruleCard__how">{text("app.rules.whenTextContains", "if the text contains any of")}</span>
                { words.map((word) => <span key={word} className="pill pill--outline ruleCard__value"><bdi>{word}</bdi></span>) }
            </>;
    };

    const action = (item) => {
        switch (item.type) {
        case HIGHLIGHT:
            return <span className="pill pill--outline"><SlIcon name="highlighter" /><FormattedMessage id="app.rules.highlights" defaultMessage="highlight what matched" /></span>;
        case SUGGEST_PLACE:
            return <span className="pill pill--outline"><SlIcon name="geo-alt" />{nameOf.place(item.point_id)}</span>;
        case SUGGEST_STATUS:
            return <ValueChip value={nameOf.value(item.key_id, item.value_id)} />;
        case HIDE:
            return <span className="pill pill--outline"><SlIcon name="eye-slash" /><FormattedMessage id="app.rules.hides" defaultMessage="hide it" /></span>;
        default:
            return null;
        }
    };

    return (
        <article className={`messageCard ruleCard ${rule.enabled ? "" : "ruleCard--off"}`}>
            <header className="ruleCard__header">
                <button
                    type="button"
                    role="switch"
                    className="ruleCard__switch"
                    aria-checked={rule.enabled}
                    aria-label={text("app.rules.onOff", "On")}
                    title={rule.enabled ? text("app.rules.on", "On") : text("app.rules.off", "Off")}
                    disabled={busy}
                    onClick={onToggle}
                />
                <h3 className="ruleCard__title">{rule.description}</h3>
                <div className="ruleCard__tools">
                    <SlIconButton name="pencil" label={text("app.rules.edit", "Edit")} disabled={busy} onClick={onEdit} />
                    <SlIconButton name="copy" label={text("app.rules.copy", "Duplicate")} disabled={busy} onClick={onCopy} />
                    <SlIconButton name="trash" label={text("app.rules.removeShort", "Remove")} disabled={busy} onClick={() => setRemoving(true)} />
                </div>
            </header>

            <div className="ruleCard__body">
                { rule.conditions.items.length > 0 &&
                    <section className="ruleCard__part">
                        <span className="ruleCard__label">
                            <FormattedMessage id="app.rules.ifLabel" defaultMessage="If" />
                        </span>
                        { conditions(rule.conditions, false) }
                    </section>
                }
                <section className="ruleCard__part">
                    <span className="ruleCard__label">
                        <FormattedMessage id="app.rules.thenLabel" defaultMessage="Then" />
                    </span>
                    <div className="ruleCard__actions">
                        { rule.actions.map((item) =>
                            <div key={item.type} className="ruleCard__action">{action(item)}{lookingFor(item)}</div>
                        )}
                    </div>
                </section>
            </div>

            { broad &&
                <p className="ruleCard__warning">
                    <SlIcon name="exclamation-triangle" />
                    { broad === "group" ?
                        <FormattedMessage
                            id="app.rules.broadGroup"
                            defaultMessage="With “any”, every message of the group meets it, whatever it says. To ask for both, choose “all”."
                        /> :
                    broad === "time" ?
                        <FormattedMessage
                            id="app.rules.broadTime"
                            defaultMessage="With “any”, every message sent then meets it, whatever it says. To ask for both, choose “all”."
                        /> :
                        <FormattedMessage
                            id="app.rules.broadNegation"
                            defaultMessage="With “any”, almost every message meets it: most do not say what it leaves out. Choose “all”."
                        />
                    }
                </p>
            }

            { removing &&
                <div className="groupsPicker__stop">
                    <p>
                        <FormattedMessage id="app.rules.removeHelp" defaultMessage="The messages it already saw keep what it did to them." />
                    </p>
                    <div className="groupsPicker__stopActions">
                        <button type="button" className="pill pill--outline pill--danger" disabled={busy} onClick={onRemove}>
                            <FormattedMessage id="app.rules.remove" defaultMessage="Remove rule" />
                        </button>
                        <button type="button" className="groupsPicker__cancel" onClick={() => setRemoving(false)}>
                            <FormattedMessage id="app.dialog.confirm.cancel" defaultMessage="Cancel" />
                        </button>
                    </div>
                </div>
            }
        </article>
    );
}
