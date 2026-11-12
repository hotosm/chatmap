import { useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";

import { ValueChip } from "../Tags";
import { tagsOf } from "../Tags/tags.js";
import { highlighted, linkOf, messageRows, renewable } from "./messages.js";

/**
 * A message in its card as rows: what rules suggest for the whole of it,
 * then each line with what it suggests, each line once and in its own
 * direction. Every suggestion says in its row what it would do (the value a
 * place has and the one it would get), why a person should look closely, or
 * that it was answered. What places already show is renewed with one click
 * at the bottom. Nothing changes a place without a person.
 *
 * @param {function} onConfirm Links the message as a suggestion says: (message, { point_id, key_id, value_id }); answers { answer } or null
 * @param {function} onAnswer Says no to a suggestion, or takes it back: (message, suggestion, rejected)
 * @param {function} onRenew Confirms at once what places already show: (message, suggestions)
 * @param {function} onChoose A suggestion lacks its place or its value: the pickers below take it, with its place if it has one
 * @param {function} onUndo Undoes the link a confirmed suggestion made: (message, link)
 */
export default function MessageLines({ message, mapData, onConfirm, onAnswer, onRenew, onChoose, onUndo }) {
    const intl = useIntl();
    const [busy, setBusy] = useState(false);
    const [failed, setFailed] = useState(false);
    const suggestions = message.suggestions || [];
    const rows = messageRows(message.text, suggestions);
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
        <button
            type="button"
            className="messageLines__no"
            disabled={busy}
            aria-label={intl.formatMessage({ id: "app.lines.no", defaultMessage: "No, it does not say this" })}
            title={intl.formatMessage({ id: "app.lines.no", defaultMessage: "No, it does not say this" })}
            onClick={() => run(() => onAnswer(message, item, true))}
        >
            <SlIcon name="x-lg" />
        </button>;

    // What a suggestion would do, as chips: the place, the value it has and the one it would get
    const said = (item) => {
        const feature = item.point_id && featureOf(item.point_id);
        const key = item.key_id && keyOf(item.key_id);
        const value = key && key.values.find((option) => option.id === item.value_id);
        const [now] = feature && key ? tagsOf(feature.properties, key.id) : [];
        // What it would change, while it waits for an answer
        const was = item.state === "pending" && now && value && now.value_id !== value.id ?
            key.values.find((option) => option.id === now.value_id) : null;
        return (
            <span className="messageLines__said">
                { feature && <span className="placeChip">{feature.properties.message}</span> }
                { was && <span className="messageLines__was"><ValueChip value={was} className="valueChip--small" /> →</span> }
                { value && <ValueChip value={value} className="valueChip--small" /> }
            </span>
        );
    };

    const answer = (item) => {
        const complete = item.point_id && item.value_id;
        if (item.state === "accepted") {
            const link = linkOf(message, item);
            return (
                <span className="messageLines__note">
                    <SlIcon name="check" />
                    <FormattedMessage id="app.lines.linked" defaultMessage="Linked" />
                    { link &&
                        <button type="button" className="messageLinks__undo" disabled={busy} onClick={() => run(() => onUndo(message, link))}>
                            <FormattedMessage id="app.messages.undo" defaultMessage="Undo" />
                        </button>
                    }
                </span>
            );
        }
        if (item.state === "rejected") {
            return (
                <span className="messageLines__note">
                    <FormattedMessage id="app.lines.saidNo" defaultMessage="You said no" />
                    <button type="button" className="messageLinks__undo" disabled={busy} onClick={() => run(() => onAnswer(message, item, false))}>
                        <FormattedMessage id="app.messages.undo" defaultMessage="Undo" />
                    </button>
                </span>
            );
        }
        if (!complete) {
            return (
                <span className="messageLines__answers">
                    <button type="button" className="messageLines__choose" disabled={busy} onClick={() => onChoose(item)}>
                        { item.point_id ?
                            <FormattedMessage id="app.lines.chooseStatus" defaultMessage="Choose its status" /> :
                            <FormattedMessage id="app.lines.choosePlace" defaultMessage="Choose the place" />
                        }
                    </button>
                    {no(item)}
                </span>
            );
        }
        if (item.unchanged && !item.doubt) {
            // Many go together in the bar at the bottom; one alone is renewed here
            return (
                <span className="messageLines__answers">
                    { same.length > 1 ?
                        <span className="messageLines__note"><FormattedMessage id="app.lines.noChange" defaultMessage="no change" /></span> :
                        <button type="button" className="messageLines__confirm" disabled={busy} onClick={() => run(() => onRenew(message, [item]))}>
                            <SlIcon name="arrow-clockwise" />
                            <FormattedMessage id="app.lines.renewOne" defaultMessage="Renew" />
                        </button>
                    }
                    {no(item)}
                </span>
            );
        }
        return (
            <span className="messageLines__answers">
                {no(item)}
                <button type="button" className="messageLines__confirm" disabled={busy} onClick={() => confirm(item)}>
                    <SlIcon name="check" />
                    <FormattedMessage id="app.lines.confirm" defaultMessage="Confirm" />
                </button>
            </span>
        );
    };

    const doubt = (item) => item.state === "pending" && item.doubt &&
        <span className="messageLines__doubt">
            { item.doubt === "question" ?
                <FormattedMessage id="app.lines.question" defaultMessage="It asks, it does not say so: confirm only if you know it" /> :
                <FormattedMessage id="app.lines.twoValues" defaultMessage="It says two values: confirm the right one" />
            }
        </span>;

    return (
        <div className="messageLines">
            { rows.map((row) =>
                <div key={row.line ?? "whole"} className={`messageLines__row ${row.suggestions.length ? "" : "messageLines__row--quiet"}`}>
                    <p className="messageLines__text" dir="auto">
                        { row.line === null ?
                            <FormattedMessage id="app.lines.byRule" defaultMessage="As the rule «{rule}» says" values={{ rule: <bdi>{row.suggestions[0].rule}</bdi> }} /> :
                            highlighted(row.text, row.suggestions.flatMap((item) => item.words || [])).map((piece, index) => piece.match ?
                                <mark key={index} className="messageCard__mark">{piece.text}</mark> : piece.text
                            )
                        }
                    </p>
                    <div className="messageLines__suggestions">
                        { row.suggestions.map((item) =>
                            <div key={item.id} className={`messageLines__suggestion messageLines__suggestion--${item.state}`}>
                                {said(item)}
                                {answer(item)}
                                {doubt(item)}
                            </div>
                        )}
                    </div>
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
        </div>
    );
}
