import { useState } from "react";
import { FormattedMessage } from "react-intl";

import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";

import { ValueChip } from "../Tags";
import { tagsOf } from "../Tags/tags.js";
import { linkOf, renewable } from "./messages.js";

/**
 * What a message suggests, under it: a row per suggestion, in the order of
 * the message (what rules say of the whole of it first, then its lines).
 * Each row says the place, the value it has and the one it would get, and
 * how to answer it; a person answers each one. What places already show is
 * renewed with one click at the bottom. Nothing changes a place without a person.
 *
 * @param {function} onConfirm Links the message as a suggestion says: (message, { point_id, key_id, value_id }); answers { answer } or null
 * @param {function} onAnswer Says no to a suggestion, or takes it back: (message, suggestion, rejected)
 * @param {function} onRenew Confirms at once what places already show: (message, suggestions)
 * @param {function} onChoose A suggestion lacks its place or its value: the pickers below take it, with its place if it has one
 * @param {function} onUndo Undoes the link a confirmed suggestion made: (message, link)
 * @param {function} onPoint Gets the line of the row pointed at, to mark it in the message; null when none is
 */
export default function MessageLines({ message, mapData, onConfirm, onAnswer, onRenew, onChoose, onUndo, onPoint }) {
    const [busy, setBusy] = useState(false);
    const [failed, setFailed] = useState(false);
    const suggestions = message.suggestions || [];
    const same = renewable(suggestions);

    const featureOf = (id) => (mapData.features || []).find((item) => item.properties.id === id && !item.properties.removed);
    const keyOf = (id) => (mapData.keys || []).find((item) => item.id === id);

    const run = async (call) => {
        setBusy(true);
        const done = await call();
        setBusy(false);
        setFailed(!done);
    };
    const confirm = (item) => run(async () => {
        const result = await onConfirm(message, { point_id: item.point_id, key_id: item.key_id, value_id: item.value_id });
        return result && result.answer;
    });
    const no = (item) =>
        <button type="button" className="messageLines__no" disabled={busy} onClick={() => run(() => onAnswer(message, item, true))}>
            <FormattedMessage id="app.lines.no" defaultMessage="Not right" />
        </button>;
    const undo = (call) =>
        <button type="button" className="messageLinks__undo" disabled={busy} onClick={() => run(call)}>
            <FormattedMessage id="app.messages.undo" defaultMessage="Undo" />
        </button>;

    // The place, and the value it has and the one it would get (the one it had, once answered)
    const said = (item) => {
        const feature = item.point_id && featureOf(item.point_id);
        const key = item.key_id && keyOf(item.key_id);
        const value = key && key.values.find((option) => option.id === item.value_id);
        const [now] = feature && key ? tagsOf(feature.properties, key.id) : [];
        const was = item.state === "pending" && now && value && now.value_id !== value.id ?
            key.values.find((option) => option.id === now.value_id) : null;
        return <>
            <span className="messageLines__place">
                { feature && <span className="placeChip">{feature.properties.message}</span> }
            </span>
            <span className="messageLines__values">
                { was && <><ValueChip value={was} className="valueChip--small" /><span aria-hidden="true" className="messageLines__arrow">→</span></> }
                { value && <ValueChip value={value} className="valueChip--small" /> }
            </span>
        </>;
    };

    const answer = (item) => {
        if (item.state === "accepted") {
            const link = linkOf(message, item);
            return <>
                <SlIcon name="check" />
                <FormattedMessage id="app.lines.linked" defaultMessage="Linked" />
                { link && <><span aria-hidden="true">·</span>{undo(() => onUndo(message, link))}</> }
            </>;
        }
        if (item.state === "rejected") {
            return <>
                <FormattedMessage id="app.lines.saidNo" defaultMessage="You said no" />
                <span aria-hidden="true">·</span>
                {undo(() => onAnswer(message, item, false))}
            </>;
        }
        if (!item.point_id || !item.value_id) {
            return <>
                {no(item)}
                <button type="button" className="messageLines__confirm" disabled={busy} onClick={() => onChoose(item)}>
                    { item.point_id ?
                        <FormattedMessage id="app.lines.chooseStatus" defaultMessage="Choose its status" /> :
                        <FormattedMessage id="app.lines.choosePlace" defaultMessage="Choose the place" />
                    }
                </button>
            </>;
        }
        if (item.unchanged && !item.doubt) {
            // Many go together in the bar at the bottom; one alone is renewed here
            return same.length > 1 ?
                <FormattedMessage id="app.lines.noChange" defaultMessage="the map shows it already" /> :
                <>
                    {no(item)}
                    <button type="button" className="messageLines__confirm" disabled={busy} onClick={() => run(() => onRenew(message, [item]))}>
                        <SlIcon name="arrow-clockwise" />
                        <FormattedMessage id="app.lines.renewOne" defaultMessage="Renew" />
                    </button>
                </>;
        }
        return <>
            {no(item)}
            <button type="button" className="messageLines__confirm" disabled={busy} onClick={() => confirm(item)}>
                <SlIcon name="check" />
                <FormattedMessage id="app.lines.confirm" defaultMessage="Confirm" />
            </button>
        </>;
    };

    // Why to look at it closely, or which rule said it
    const note = (item) => {
        if (item.state === "pending" && item.doubt) {
            return <p className="messageLines__note messageLines__note--doubt">
                <SlIcon name="info-circle" />
                { item.doubt === "question" ?
                    <FormattedMessage id="app.lines.question" defaultMessage="It asks, it does not say so: confirm only if you know it" /> :
                    <FormattedMessage id="app.lines.twoValues" defaultMessage="It says two values: confirm the right one" />
                }
            </p>;
        }
        return item.line === null && item.rule ?
            <p className="messageLines__note">
                <FormattedMessage id="app.lines.byRule" defaultMessage="As the rule «{rule}» says" values={{ rule: <bdi>{item.rule}</bdi> }} />
            </p> : null;
    };

    return (
        <section className="messageLines" onMouseLeave={() => onPoint(null)}>
            <h4 className="messageLines__label">
                <FormattedMessage id="app.lines.suggests" defaultMessage="Suggests" />
            </h4>
            { suggestions.map((item) =>
                <div
                    key={item.id}
                    className={`messageLines__row messageLines__row--${item.state}`}
                    onMouseEnter={() => onPoint(item.line)}
                    onFocus={() => onPoint(item.line)}
                >
                    {said(item)}
                    <span className="messageLines__answers">{answer(item)}</span>
                    {note(item)}
                </div>
            )}
            { same.length > 1 &&
                <div className="messageLines__renew">
                    <span>
                        <FormattedMessage
                            id="app.lines.sameCount"
                            defaultMessage="{count, plural, one {# line says what the map already shows} other {# lines say what the map already shows}}"
                            values={{ count: same.length }}
                        />
                    </span>
                    <button type="button" className="messageLines__confirm" disabled={busy} onClick={() => run(() => onRenew(message, same))}>
                        <SlIcon name="arrow-clockwise" />
                        <FormattedMessage id="app.lines.renew" defaultMessage="Renew {count}" values={{ count: same.length }} />
                    </button>
                </div>
            }
            { failed &&
                <p className="messageLinker__notice messageLinker__notice--error" role="alert">
                    <FormattedMessage id="app.messages.notSaved" defaultMessage="It could not be saved. Try again." />
                </p>
            }
        </section>
    );
}
