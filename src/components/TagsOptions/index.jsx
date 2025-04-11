
import React from "react";

export default function TagsOptions({ tags, onSelectTag, selectedTag }) {
    return (
        Object.keys(tags).length > 0 ?
        <sl-dropdown>
            <sl-button size="small" slot="trigger" caret>
                { selectedTag ? selectedTag : "Tags" }
                <sl-icon slot="prefix" name="tags"></sl-icon>
            </sl-button>
            <sl-menu>
                <sl-menu-item key="all" onClick={() => onSelectTag(null)}>
                    {!selectedTag ?
                    <strong>All</strong> : "All"}
                </sl-menu-item>
                {Object.keys(tags).map(key =>
                    <sl-menu-item key={key} onClick={() => onSelectTag(key)}>
                        {selectedTag && selectedTag == key ?
                            <strong>{key} ({tags[key]})</strong>
                        : 
                            `${key} (${tags[key]})`
                        }
                    </sl-menu-item>
                )}
            </sl-menu>
        </sl-dropdown>
        : ""
    );
}
