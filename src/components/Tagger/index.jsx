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
        if (event.key === 'Enter' && textRef.current.value) {
            onAddTag && onAddTag(textRef.current.value);
            textRef.current.value = "";
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
                {tags && tags.map(tag =>
                    <sl-button
                        variant="neutral"
                        size="small"
                        outline
                        onClick={() => removeTagHandler(tag)}
                        pill
                        key={`${tag}`}
                    >
                        <sl-icon name="x-circle" slot="prefix"></sl-icon>
                        {tag}
                    </sl-button>
                )}
            </div>
        </div>
    );
}
