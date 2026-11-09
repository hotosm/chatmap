import { useRef, useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";
import "@shoelace-style/shoelace/dist/components/divider/divider.js";

import KeyValues from "./KeyValues.jsx";
import { freeTags, selectable, tagsOf } from "./tags.js";

/**
 * The "+" at the end of the tags of a point. It floats over the map, so the
 * popup does not grow: first the keys of the map the point can still take
 * (picking one of their values, or writing one), then a free tag,
 * suggesting the ones the map already uses.
 */
export default function AddTag({ keys, properties, allTags, onSetTag, onAddTag }) {
    const intl = useIntl();
    const dropdown = useRef();
    const [text, setText] = useState("");

    const tags = freeTags(properties.tags);
    // A key with one value is offered while the point has none; a key with many, while it has something left
    const open = keys
        .map(key => {
            const given = tagsOf(properties, key.id).map(tag => tag.value_id);
            return { key, given, options: selectable(key).filter(value => !given.includes(value.id)) };
        })
        .filter(({ key, given, options }) =>
            (!key.single || given.length === 0) && (!key.closed || options.length > 0)
        );

    const typed = text.trim();
    const suggestions = (allTags || [])
        .filter(tag => tag !== "__undefined" && tag !== "__all")
        .filter(tag => !tags.includes(tag))
        .filter(tag => tag.toLowerCase().startsWith(typed.toLowerCase()));
    const isNew = typed && !(allTags || []).includes(typed) && !tags.includes(typed);

    const done = () => {
        setText("");
        dropdown.current && dropdown.current.hide();
    };
    // The panel closes once the value is saved; if it is not, the popup tells
    const give = async (keyId, change) => {
        if (await onSetTag(keyId, change)) done();
    };
    const addTag = (tag) => { onAddTag(tag); done(); };

    const handleKeyDown = (event) => {
        if (event.key === "Enter" && typed) {
            event.preventDefault();
            if (!tags.includes(typed)) addTag(typed);
        }
    };

    return (
        <sl-dropdown hoist ref={dropdown}>
            <button
                slot="trigger"
                className="pill pointTags__add"
                aria-label={intl.formatMessage({ id: "app.tags.add", defaultMessage: "Add tag" })}
                title={intl.formatMessage({ id: "app.tags.add", defaultMessage: "Add tag" })}
            >
                +
            </button>
            <div className="popoverPanel pointTags__panel">
                <KeyValues keys={open} onPick={give} />
                { open.length > 0 && <sl-divider /> }
                <div className="popoverPanel__title">
                    <FormattedMessage id="app.tags.newFreeTag" defaultMessage="New tag" />
                </div>
                <SlInput
                    size="small"
                    value={text}
                    autocomplete="off"
                    placeholder={intl.formatMessage({ id: "app.yourTagHere", defaultMessage: "Your tag here" })}
                    onSlInput={(event) => setText(event.target.value)}
                    onKeyDown={handleKeyDown}
                />
                <div className="pointTags__suggestions">
                    { suggestions.map(tag =>
                        <button key={tag} className="popoverPanel__option" onClick={() => addTag(tag)}>
                            {tag}
                        </button>
                    )}
                    { isNew &&
                        <button className="popoverPanel__option" onClick={() => addTag(typed)}>
                            <FormattedMessage id="app.tags.create" defaultMessage="Create “{tag}”" values={{ tag: typed }} />
                        </button>
                    }
                </div>
            </div>
        </sl-dropdown>
    );
}
