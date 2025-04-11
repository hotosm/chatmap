import React, { useRef } from "react";
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
        }
    }

    return (
        <div className="tagger">
            <input
                onKeyDown={handleKeyDown}
                ref={textRef}
                className="textInput"
                type="text"
                placeholder="Your tag here"
            />
            <div className="tags">
                {Object.keys(tags).map(key =>
                    <span
                        onClick={() => removeTagHandler(key)}
                        className="tag"
                        key={`${key}_${tags[key]}`}
                    > {key}{tags[key] ? `=${tags[key]}` : ""}
                    </span>
                )}
            </div>
        </div>
    );
}
