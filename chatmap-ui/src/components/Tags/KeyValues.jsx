import { useState } from "react";
import { useIntl } from "react-intl";

import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";

// A text field that gives its text on Enter
function TextField({ placeholder, onText }) {
    const [text, setText] = useState("");

    const handleKeyDown = (event) => {
        if (event.key === "Enter" && text.trim()) {
            event.preventDefault();
            onText(text.trim());
            setText("");
        }
    };

    return (
        <SlInput
            size="small"
            value={text}
            autocomplete="off"
            placeholder={placeholder}
            onSlInput={(event) => setText(event.target.value)}
            onKeyDown={handleKeyDown}
        />
    );
}

/**
 * The values that can be given for some keys, inside a panel: under the name
 * of each key, its options with their color, or a field to write one.
 *
 * @param {array} keys [{ key, options }]: each key with the options offered
 * @param {function} onPick Gets the id of the key and the change: { action: "set", value_id | value }
 */
export default function KeyValues({ keys, onPick }) {
    const intl = useIntl();

    return keys.map(({ key, options }) =>
        <section key={key.id} className="pointTags__panelKey">
            <div className="popoverPanel__title">{key.key}</div>
            { key.closed ?
                options.map(value =>
                    <button
                        key={value.id}
                        type="button"
                        className="popoverPanel__option"
                        onClick={() => onPick(key.id, { action: "set", value_id: value.id })}
                    >
                        <span className="tags__dot" style={{ backgroundColor: value.color || undefined }} />
                        {value.value}
                    </button>
                )
            :
                <TextField
                    placeholder={intl.formatMessage({ id: "app.tags.write", defaultMessage: "Write and press Enter" })}
                    onText={(value) => onPick(key.id, { action: "set", value })}
                />
            }
        </section>
    );
}
