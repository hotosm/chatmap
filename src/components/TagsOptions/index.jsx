
import React from "react";

export default function TagsOptions({ tags }) {
    return (
        <div className="tagsOptions">
            {Object.keys(tags).map(key =>
                <span
                    className="tag"
                    key={`${key}_${tags[key]}`}
                > {key}{tags[key] ? `=${tags[key]}` : ""}
                </span>
            )}
        </div>
    );
}
