import { useRef } from "react";
import "./tagger.css";

export default function Tagger({
    onAddTag,
    onRemoveTag,
    onFocus,
    onBlur,
    tags,
    allTags,
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
            <sl-dropdown>
                <sl-input
                    size="small"
                    onKeyDown={handleKeyDown}
                    ref={textRef}
                    onClick={() => textRef.current.focus()}
                    onFocus={() => onFocus && onFocus()}
                    onBlur={() => onBlur && onBlur()}
                    placeholder={placeholder}
                    slot="trigger"
                >
                    <sl-icon name="tags" slot="suffix"></sl-icon>
                </sl-input>
                { allTags && allTags.length > 0 ? 
                <sl-menu>
                    {allTags.map(tag =>
                        <sl-menu-item
                            value={tag}
                            key={tag}
                            onClick={() => {
                                if (tags.indexOf(tag) === -1) {
                                    onAddTag(tag)
                                }
                            }}
                        >
                            {tag}
                        </sl-menu-item>
                    )}
                </sl-menu>
                : null}
            </sl-dropdown>
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
