import { Fragment } from "react";
import { FormattedMessage } from "react-intl";
import "@shoelace-style/shoelace/dist/components/divider/divider.js";
import "@shoelace-style/shoelace/dist/components/menu-label/menu-label.js";

import { colorKeys, keyFilter, keyFilterOf, shownValueCounts, UNKNOWN } from "./tags.js";
import useNow from "./useNow.js";

const unknownName = <FormattedMessage id="app.tags.unknown" defaultMessage="Unknown" />;

/**
 * The options of the keys of a map in its filter, before its free tags: for
 * each key with one value and a list, how many points show each option now,
 * so an expired one counts as unknown. Items go straight in the menu, so the
 * keyboard reaches them.
 */
export function TagFilterItems({ keys, features, selected, onSelect }) {
    const filterable = colorKeys(keys);
    const now = useNow(filterable.length > 0);
    if (filterable.length === 0) return null;
    const current = keyFilterOf(selected);

    return (<>
        { filterable.map((key) =>
            <Fragment key={key.id}>
                <sl-divider />
                <sl-menu-label>{key.key}</sl-menu-label>
                { shownValueCounts(features, key, now).map((option) => {
                    const chosen = current && current.keyId === key.id && current.valueId === option.id;
                    const label = <>{option.value || unknownName} ({option.count})</>;
                    return (
                        <sl-menu-item key={option.id} onClick={() => onSelect(keyFilter(key.id, option.id))}>
                            <span
                                slot="prefix"
                                className={`tags__dot tagFilter__dot ${option.id === UNKNOWN ? "tagFilter__dot--unknown" : ""}`}
                                style={option.color ? { backgroundColor: option.color } : {}}
                            />
                            { chosen ? <strong>{label}</strong> : label }
                        </sl-menu-item>
                    );
                })}
            </Fragment>
        )}
        <sl-divider />
        <sl-menu-label><FormattedMessage id="app.tags.freeTags" defaultMessage="Free tags" /></sl-menu-label>
    </>);
}

// The option the map is filtered by, or null when it is a free tag
export function tagFilterName(keys, filter) {
    const chosen = keyFilterOf(filter);
    if (!chosen) return null;
    if (chosen.valueId === UNKNOWN) return unknownName;
    const key = (keys || []).find((item) => item.id === chosen.keyId);
    const value = key && key.values.find((item) => item.id === chosen.valueId);
    return value ? value.value : null;
}
