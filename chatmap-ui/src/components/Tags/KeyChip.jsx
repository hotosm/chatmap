import { FormattedMessage, useIntl } from "react-intl";
import "@shoelace-style/shoelace/dist/components/divider/divider.js";

import TimeAgo from "./TimeAgo.jsx";
import { isExpired, selectable, textOn } from "./tags.js";

// "20 Oct, 08:30"
const WHEN = { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" };

// "Fuel: There is · since 08:30 · confirmed 2 hours ago", to read on hover
const useTitle = (key, value, tag) => {
    const intl = useIntl();
    const since = intl.formatDate(tag.since, WHEN);
    const confirmed = intl.formatDate(tag.confirmed_at, WHEN);
    return `${key.key}: ${value} · ${intl.formatMessage(
        { id: "app.tags.sinceConfirmed", defaultMessage: "since {since} · confirmed {confirmed}" },
        { since, confirmed },
    )}`;
};

/**
 * A value of a key with a list, as a chip with its color. When its value
 * expired it shows as unknown. Who can edit the point opens it to confirm
 * the value, change it or take it out.
 */
export default function KeyChip({ keyItem, tag, now, onSetTag, showEditOptions }) {
    const intl = useIntl();
    const value = keyItem.values.find(item => item.id === tag.value_id);
    const title = useTitle(keyItem, value ? value.value : "", tag);
    if (!value) return null;

    const chip = isExpired(value, tag, now) ?
        <span className="pointTags__chip pointTags__chip--unknown" title={title}>
            <FormattedMessage id="app.tags.unknown" defaultMessage="Unknown" />
        </span> :
        <span
            className={`pointTags__chip ${value.color ? "" : "pointTags__chip--plain"}`}
            style={value.color ? { backgroundColor: value.color, color: textOn(value.color) } : {}}
            title={title}
        >
            {value.value}
        </span>;

    if (!showEditOptions) return chip;

    // A key with many values: each one is taken out on its own
    if (!keyItem.single) {
        return (
            <span className="pointTags__chip pointTags__chip--many" title={title}>
                {chip}
                <button
                    className="pointTags__remove"
                    aria-label={intl.formatMessage({ id: "app.tags.remove", defaultMessage: "Remove {tag}" }, { tag: value.value })}
                    onClick={() => onSetTag({ action: "remove", value_id: value.id })}
                >
                    ×
                </button>
            </span>
        );
    }

    // An archived key keeps its value, but it can only be taken out
    const others = keyItem.archived ? [] : selectable(keyItem).filter(item => item.id !== value.id);
    const canConfirm = !keyItem.archived && !value.archived;
    return (
        <sl-dropdown hoist>
            <button
                slot="trigger"
                className="pointTags__trigger"
                title={title}
                aria-label={intl.formatMessage({ id: "app.tags.change", defaultMessage: "Change {key}" }, { key: keyItem.key })}
            >
                {chip}
            </button>
            <sl-menu className="pointTags__menu">
                {/* The same value again confirms it: it keeps its "since" */}
                { canConfirm && <>
                    <sl-menu-item onClick={() => onSetTag({ action: "set", value_id: value.id })}>
                        <span slot="prefix" className="tags__dot" style={{ backgroundColor: value.color || undefined }} />
                        <FormattedMessage id="app.tags.confirm" defaultMessage="Still {value}" values={{ value: value.value }} />
                    </sl-menu-item>
                    <sl-divider />
                </>}
                {/* A point keeps an archived value, but it cannot be picked again */}
                {others.map(item =>
                    <sl-menu-item key={item.id} onClick={() => onSetTag({ action: "set", value_id: item.id })}>
                        <span slot="prefix" className="tags__dot" style={{ backgroundColor: item.color || undefined }} />
                        {item.value}
                    </sl-menu-item>
                )}
                { others.length > 0 && <sl-divider /> }
                <sl-menu-item onClick={() => onSetTag({ action: "remove" })}>
                    <span slot="prefix" className="tags__dot tags__dot--none" />
                    <FormattedMessage id="app.tags.removeValue" defaultMessage="Remove {key}" values={{ key: keyItem.key }} />
                </sl-menu-item>
            </sl-menu>
        </sl-dropdown>
    );
}

// "Open since 08:30 · confirmed 2 hours ago", or the last value known when it expired
export function TagTimes({ keyItem, tag, now }) {
    const intl = useIntl();
    const value = keyItem.values.find(item => item.id === tag.value_id);
    if (!value) return null;
    const ago = <TimeAgo datetime={tag.confirmed_at} />;

    return (
        <span className="pointTags__time">
            { isExpired(value, tag, now) ?
                <FormattedMessage
                    id="app.tags.lastKnown"
                    defaultMessage="Last: {value}, {ago}"
                    values={{ value: value.value, ago }}
                />
            : tag.since !== tag.confirmed_at ?
                <FormattedMessage
                    id="app.tags.sinceConfirmedAgo"
                    defaultMessage="{value} since {since} · confirmed {ago}"
                    values={{
                        value: value.value,
                        since: intl.formatDate(tag.since, WHEN),
                        ago,
                    }}
                />
            :
                <FormattedMessage
                    id="app.tags.confirmedAgo"
                    defaultMessage="{value} · confirmed {ago}"
                    values={{ value: value.value, ago }}
                />
            }
        </span>
    );
}
