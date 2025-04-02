import React, { useRef } from "react";
import useTagger from './useTagger';
import "./tagger.css";

export default function Tagger({ featureId }) {
    const [add, remove, tags] = useTagger();
    const textRef = useRef();

    const addTagHandler = () => {
        const keyval = textRef.current.value.split("=");
        if (keyval[0]) {
            const [key, val] = [keyval[0], keyval[1]];
            add(featureId, key, val || "");
            textRef.current.value = "";
        }
    };

    const removeTagHandler = (key) => {
        remove(featureId, key);
    };

    const featureTags = tags(featureId) || {};

    return (
        <>
            <button className="secondaryButton smallButton" onClick={addTagHandler}>Add tag</button>
            <input ref={textRef} className="textInput" type="text" placeholder="Your tag here" />
            <div className="tags">
                {Object.keys(featureTags).map(key =>
                    <span
                        onClick={() => removeTagHandler(key)}
                        className="tag"
                        key={`${key}_${tags[key]}`}
                    > {key}{featureTags[key] ? `=${featureTags[key]}` : ""}</span>
                )}
            </div>
        </>
    );
}
