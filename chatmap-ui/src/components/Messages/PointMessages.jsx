import { useCallback, useEffect, useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";
import SlSpinner from "@shoelace-style/shoelace/dist/react/spinner/index.js";

import { useConfigContext } from "../../context/ConfigContext.jsx";
import BottomSheet from "../BottomSheet";
import usePhone from "../BottomSheet/usePhone.js";
import { timeAgo } from "../TimeAgo";
import { ValueChip, usesKeys } from "../Tags";
import { groupMessagesOn, messagesOn, pageOf } from "./messages.js";
import { EXPIRED, ON_MAP, TAKEN_OUT, UNDONE, noteOf, placeHistory, valuesInForce } from "./placeHistory.js";
import PlaceNames from "./PlaceNames.jsx";
import useGroupName from "./useGroupName.js";
import useMessagesApi from "./useMessagesApi.js";
import "./placeHistory.css";

// "10 minutes ago", as a text to put inside another
const useAgo = () => {
    const intl = useIntl();
    return useCallback((datetime, now) => {
        const ago = timeAgo(datetime, now);
        return ago ? intl.formatRelativeTime(ago.value, ago.unit, { numeric: "auto" }) : "";
    }, [intl]);
};

// What the note under a change says (see noteOf)
const NOTES = {
    undone: { id: "app.placeHistory.undone", defaultMessage: "Undone by you" },
    gone: { id: "app.placeHistory.gone", defaultMessage: "Its text was removed when the map stopped keeping it; the change stays" },
    manual: { id: "app.placeHistory.manual", defaultMessage: "Set by hand · no message" },
    other: { id: "app.placeHistory.other", defaultMessage: "Brought with the place from another map" },
    older: { id: "app.placeHistory.older", defaultMessage: "Older: a newer report rules" },
    takenOut: { id: "app.placeHistory.takenOutNote", defaultMessage: "It took the value out of the place" },
    byRule: { id: "app.placeHistory.byRule", defaultMessage: "Suggested, and linked by you" },
    linked: { id: "app.placeHistory.linked", defaultMessage: "Linked by you" },
};

/**
 * What the map shows today for the place, one row per key: its values,
 * since when, and how long they last before they show as unknown.
 */
function InForce({ rows, now }) {
    const intl = useIntl();
    const ago = useAgo();

    const metaOf = (key, values) => {
        const since = ago(values[0].since, now);
        // A key with many values: only since when it has the first one
        if (values.length > 1 || !key.single) {
            return intl.formatMessage({ id: "app.placeHistory.since", defaultMessage: "since {since}" }, { since });
        }
        const { value, expiresAt, expired } = values[0];
        if (expired) {
            return intl.formatMessage(
                { id: "app.placeHistory.unknownSince", defaultMessage: "unknown since {when}: nobody confirmed it" },
                { when: ago(expiresAt, now) },
            );
        }
        if (!expiresAt) {
            return intl.formatMessage({ id: "app.placeHistory.noExpiry", defaultMessage: "since {since} · does not expire" }, { since });
        }
        return intl.formatMessage(
            { id: "app.placeHistory.lasts", defaultMessage: "since {since} · lasts {lasts}, then unknown" },
            { since, lasts: intl.formatNumber(value.expires_after, { style: "unit", unit: "hour", unitDisplay: "short" }) },
        );
    };

    return (
        <dl className="placeHistory__inForce">
            { rows.map(({ key, values }) =>
                <div key={key.id} className="placeHistory__keyRow">
                    <dt className="pointMessages__muted">{key.key}</dt>
                    <dd className="placeHistory__values">
                        { values.map(({ tag, value, expired }) => expired ?
                            <span key={tag.value_id || tag.value} className="pill pill--outline">
                                <FormattedMessage id="app.tags.unknown" defaultMessage="Unknown" />
                            </span> :
                            <ValueChip key={tag.value_id || tag.value} value={value} />
                        )}
                        <span className="pointMessages__muted placeHistory__meta">{metaOf(key, values)}</span>
                    </dd>
                </div>
            )}
        </dl>
    );
}

// One change of the place: the message it comes from, the value it gave, what it is today and the way to undo it
function Entry({ entry, now, busy, onUndo }) {
    const ago = useAgo();
    const groupName = useGroupName();
    const { change, state, value, gone } = entry;
    const undone = state === UNDONE;

    return (
        <li className={`messageCard placeHistory__entry placeHistory__entry--${state}`}>
            { (change.message_id || gone) &&
                <p className="messageCard__text">
                    { change.message_text ||
                        <span className="pointMessages__muted">
                            { gone ?
                                <FormattedMessage id="app.messages.gone" defaultMessage="The message is no longer kept" /> :
                                <FormattedMessage id="app.messages.withoutText" defaultMessage="A location, without text" />
                            }
                        </span>
                    }
                </p>
            }
            <div className="placeHistory__row">
                <span className="pointMessages__muted">{change.key}</span>
                <ValueChip value={value} className={state === TAKEN_OUT ? "placeHistory__takenOut" : ""} />
                { state === ON_MAP &&
                    <span className="pill placeHistory__state">
                        <FormattedMessage id="app.placeHistory.onMap" defaultMessage="On the map" />
                    </span>
                }
                { state === EXPIRED &&
                    <span className="pill pill--outline placeHistory__state">
                        <FormattedMessage id="app.placeHistory.expired" defaultMessage="Expired" />
                    </span>
                }
                { state === TAKEN_OUT &&
                    <span className="pill pill--outline placeHistory__state">
                        <FormattedMessage id="app.placeHistory.takenOut" defaultMessage="Taken out" />
                    </span>
                }
                <span className="messageCard__meta placeHistory__when">
                    <time dateTime={change.happened_at} title={new Date(change.happened_at).toLocaleString()}>
                        { change.message_id ?
                            <FormattedMessage
                                id="app.placeHistory.agoIn"
                                defaultMessage="{ago} in {group}"
                                values={{ ago: ago(change.happened_at, now), group: <b>{groupName(change.group_name)}</b> }}
                            /> :
                            ago(change.happened_at, now)
                        }
                    </time>
                </span>
            </div>
            <div className="placeHistory__row">
                <span className="pointMessages__muted placeHistory__note">
                    <FormattedMessage {...NOTES[noteOf(entry)]} />
                </span>
                <button
                    type="button"
                    className="messageLinks__undo placeHistory__action"
                    disabled={busy}
                    onClick={() => onUndo(change, !undone)}
                >
                    { undone ?
                        <>
                            <SlIcon name="arrow-clockwise" />
                            <FormattedMessage id="app.placeHistory.bringBack" defaultMessage="Bring back" />
                        </> :
                        <FormattedMessage id="app.messages.undo" defaultMessage="Undo" />
                    }
                </button>
            </div>
        </li>
    );
}

/**
 * The history of the point chosen on the map, in a panel at its side: what
 * the map shows for it today, and every change of its keys, newest first,
 * from messages or by hand: the one in force, older ones, undone ones (to
 * bring back) and those whose message is no longer kept. Only for the owner
 * of a map whose messages are shown (see messagesOn). It follows the popup
 * of the point: it closes with it.
 *
 * On a phone it goes in a BottomSheet, with the name of the place as its
 * title; closing it lets the point go.
 *
 * @param {object} point The point chosen (a feature), or null
 * @param {function} onChange Called after a change is undone or brought back: what the point has changed
 * @param {function} onClose Lets the point go, from the sheet on a phone
 */
export default function PointMessages({ mapData, data, point, onChange, onClose }) {
    const intl = useIntl();
    const { config } = useConfigContext();
    const { readPointHistory, setLinkUndone } = useMessagesApi();
    const [changes, setChanges] = useState(null);
    const [failed, setFailed] = useState(false);
    const [busy, setBusy] = useState(null);
    const phone = usePhone();
    const on = groupMessagesOn(config) && messagesOn(mapData, usesKeys(data));
    const pointId = point && point.properties.id;

    const read = useCallback(async (current = { on: true }) => {
        const history = await readPointHistory(pointId);
        if (!current.on) return;
        setFailed(!history);
        setChanges(history ? history.changes || [] : []);
    }, [pointId, readPointHistory]);

    useEffect(() => {
        if (!on || !pointId) return;
        const current = { on: true };
        setChanges(null);
        read(current);
        return () => { current.on = false; };
    }, [on, pointId, read]);

    if (!on || !point) return null;

    // What the point has now, as the map read it last: the chosen feature may be older
    const now = Date.now();
    const feature = (data.features || []).find((item) => item.properties.id === pointId) || point;
    const tags = feature.properties.point_tags || [];
    const inForce = valuesInForce(tags, data.keys, now);
    const entries = changes && placeHistory(changes, tags, data.keys, now);

    const setUndone = async (change, undone) => {
        setBusy(change.id);
        const saved = await setLinkUndone(change.id, undone);
        setBusy(null);
        setFailed(!saved);
        if (!saved) return;
        await read();
        onChange && onChange();
    };

    // The way to the page of the messages: under the empty state, or under the list
    const toInbox =
        <a className="pill pill--outline pointMessages__more" href={pageOf(`/map/${mapData.id}/messages`)}>
            <FormattedMessage id="app.messages.toInbox" defaultMessage="Go to the messages" />
            <SlIcon name="arrow-right" />
        </a>;
    const empty = entries && entries.length === 0 && !failed;

    const label = intl.formatMessage({ id: "app.placeHistory.label", defaultMessage: "History of this place" });
    const content = <>
            <header className="pointMessages__header">
                { !phone && <h2 className="pointMessages__title">{point.properties.message}</h2> }
                { inForce.length > 0 && <InForce rows={inForce} now={now} /> }
            </header>

            <PlaceNames pointId={pointId} />

            { entries === null && <SlSpinner className="pointMessages__loading" /> }
            { empty &&
                <div className="pointMessages__empty">
                    <SlIcon name="chat-left-text" />
                    <p>
                        <FormattedMessage
                            id="app.placeHistory.empty"
                            defaultMessage="This place has no history yet. Link messages to it from the messages page, or give it a value by hand."
                        />
                    </p>
                    {toInbox}
                </div>
            }
            { entries && entries.length > 0 &&
                <section className="placeHistory">
                    <h3 className="pointMessages__subtitle">
                        <FormattedMessage id="app.placeHistory.title" defaultMessage="History · newest first" />
                    </h3>
                    <ul className="pointMessages__list">
                        { entries.map((entry) =>
                            <Entry
                                key={entry.change.id}
                                entry={entry}
                                now={now}
                                busy={busy === entry.change.id}
                                onUndo={setUndone}
                            />
                        )}
                    </ul>
                </section>
            }
            { failed &&
                <p className="messageLinker__notice messageLinker__notice--error" role="alert">
                    <FormattedMessage id="app.placeHistory.notRead" defaultMessage="The history of this place could not be read or changed. Try again." />
                </p>
            }
            { !empty && toInbox }
    </>;

    return phone ?
        <BottomSheet open title={point.properties.message} label={label} onClose={() => onClose && onClose()} className="pointMessages--sheet">
            {content}
        </BottomSheet> :
        <aside className="pointMessages" aria-label={label}>{content}</aside>;
}
