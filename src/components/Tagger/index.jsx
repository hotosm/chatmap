import React, { useRef, useEffect } from "react";
import "./tagger.css";

export default function Tagger({
    onAddTag,
    onRemoveTag,
    tags
}) {
    const textRef = useRef();

    const removeTagHandler = (key) => {
        onRemoveTag && onRemoveTag(key);
    };

    const handleKeyDown = (event) => {
        if (event.key === 'Enter') {
            const keyval = textRef.current.value.split("=");
            if (keyval[0]) {
                const [key, value] = [keyval[0], keyval[1] || ""];
                onAddTag && onAddTag(key, value);
                textRef.current.value = "";
            }
            event.preventDefault();
        }
    }

    useEffect(() => {
        textRef.current.focus()
    });
    

    return (
        <div className="tagger">
            <sl-input
                size="small"
                onKeyDown={handleKeyDown}
                ref={textRef}
                autofocus
                placeholder="Your tag here"
            >
                <sl-icon name="tags" slot="suffix"></sl-icon>
            </sl-input>
            <div className="tags">
                {Object.keys(tags).map(key =>
                    <sl-button
                        variant="neutral"
                        size="small"
                        outline
                        onClick={() => removeTagHandler(key)}
                        pill
                        key={`${key}_${tags[key]}`}
                    >
                        <sl-icon name="x-circle" slot="prefix"></sl-icon>
                        {key}{tags[key] ? `=${tags[key]}` : ""}
                    </sl-button>
                )}
            </div>
        </div>
    );
}
