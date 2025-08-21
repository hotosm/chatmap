import { useRef } from "react";
import "./tagger.css";

export default function Tagger({
    onAddTag,
    onRemoveTag,
    onFocus,
    onBlur,
    tags,
    placeholder
}) {
    const textRef = useRef();

    // Remove a tag
    const removeTagHandler = (key) => {
        onRemoveTag && onRemoveTag(key);
    };

    // Handle 'Enter' key / add tags
    const handleKeyDown = (event) => {
        if (event.key === 'Enter' && textRef.current.value) {
            onAddTag && onAddTag(textRef.current.value);
            textRef.current.value = "";
            event.preventDefault();
        }
    }

    return (
        <div className="tagger">
            <sl-input
                size="small"
                onKeyDown={handleKeyDown}
                ref={textRef}
                onClick={() => textRef.current.focus()}
                onFocus={() => onFocus && onFocus()}
                onBlur={() => onBlur && onBlur()}
                placeholder={placeholder}
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
