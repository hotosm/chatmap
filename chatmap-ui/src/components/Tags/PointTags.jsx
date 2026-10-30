import { useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import AddTag from "./AddTag.jsx";
import KeyChip, { TagTimes } from "./KeyChip.jsx";
import { activeKeys, freeTags, keepArrows, tagsOf } from "./tags.js";
import useNow from "./useNow.js";

/**
 * The tags of a point in one row of chips: the values it has for the keys of
 * the map, then its free tags, and a "+" to add either. Under them, since
 * when and when it was confirmed, for the key the map is colored by.
 * keys, colorKey and setTag come from useMapTags; onChange gets the
 * properties of the point once a value is saved.
 */
export default function PointTags({
    keys,
    colorKey,
    setTag: saveTag,
    properties,
    allTags,
    onChange,
    onAddTag,
    onRemoveTag,
    showEditOptions
}) {
    const intl = useIntl();
    const now = useNow();
    const [failed, setFailed] = useState(false);
    const tags = freeTags(properties.tags);

    // A change the API does not take is told here, under the chips
    const setTag = async (keyId, change) => {
        const saved = await saveTag(properties, keyId, change);
        setFailed(!saved);
        if (saved) onChange(saved);
        return Boolean(saved);
    };
    // The keys the point has a value for, archived ones included: it keeps them
    const given = keys
        .map(key => ({ key, has: tagsOf(properties, key.id) }))
        .filter(({ has }) => has.length > 0);
    const colorTag = given.find(({ key }) => key.id === colorKey);

    if (given.length === 0 && tags.length === 0 && !showEditOptions) return null;

    const removeButton = (label, onClick) => showEditOptions &&
        <button
            className="pointTags__remove"
            aria-label={intl.formatMessage({ id: "app.tags.remove", defaultMessage: "Remove {tag}" }, { tag: label })}
            onClick={onClick}
        >
            ×
        </button>;

    return (
        <div className="pointTags" onKeyDown={keepArrows}>
            <div className="pointTags__row">
                { given.map(({ key, has }) => has.map(tag =>
                    key.closed ?
                        <KeyChip
                            key={`${key.id}-${tag.value_id}`}
                            keyItem={key}
                            tag={tag}
                            now={now}
                            onSetTag={(change) => setTag(key.id, change)}
                            showEditOptions={showEditOptions}
                        />
                    :
                        <span key={`${key.id}-${tag.value}`} className="pill pointTags__chip--free" title={key.key}>
                            <span className="pointTags__key">{key.key}:</span> {tag.value}
                            {removeButton(tag.value, () => setTag(key.id, { action: "remove", value: tag.value }))}
                        </span>
                ))}
                { tags.map(tag =>
                    <span key={tag} className="pill pointTags__chip--free">
                        {tag}
                        {removeButton(tag, () => { setFailed(false); onRemoveTag(tag); })}
                    </span>
                )}
                { showEditOptions &&
                    <AddTag
                        keys={activeKeys(keys)}
                        properties={properties}
                        allTags={allTags}
                        onSetTag={setTag}
                        onAddTag={(tag) => { setFailed(false); onAddTag(tag); }}
                    />
                }
            </div>
            { colorTag && colorTag.key.closed && colorTag.key.single &&
                <TagTimes keyItem={colorTag.key} tag={colorTag.has[0]} now={now} />
            }
            { failed &&
                <span className="pointTags__error" role="alert">
                    <FormattedMessage id="app.tags.notChanged" defaultMessage="It could not be changed. Try again." />
                </span>
            }
        </div>
    );
}
