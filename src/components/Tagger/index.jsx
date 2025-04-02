import React, { useRef } from "react";
import useTagger from './useTagger';
import "./tagger.css";

export default function Tagger() {
    const [tags, addTag] = useTagger();
    const textRef = useRef();

    const addTagHandler = () => {
        const keyval = textRef.current.value.split("=");
        if (keyval[0]) {
            addTag(keyval[0], keyval[1] || "");
        }
    };

    return (
        <>
            <button className="secondaryButton smallButton" onClick={addTagHandler}>Add tag</button>
            <input ref={textRef} className="textInput" type="text" placeholder="Your tag here" />
            <div className="tags">
                {Object.keys(tags).map(key =>
                    <span className="tag" key={`${key}_${tags[key]}`}>{key}{tags[key] && "="}{tags[key]}</span>
                )}
            </div>
        </>
    );
}
