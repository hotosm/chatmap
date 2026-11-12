import { useEffect, useMemo, useRef, useState } from "react";
import { FormattedMessage, FormattedNumber, useIntl } from "react-intl";

import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";

import { placesNamed } from "./messages.js";

// How many places the panel lists at once: the rest are found by name
const SHOWN = 30;

// "350 m", "1.2 km"
function Distance({ meters }) {
    return meters < 1000 ?
        <FormattedNumber value={meters} style="unit" unit="meter" maximumFractionDigits={0} /> :
        <FormattedNumber value={meters / 1000} style="unit" unit="kilometer" maximumFractionDigits={1} />;
}

/**
 * A pill to pick a place of the map, in a panel: found by its name, and
 * nearest first when the message says where it was sent from.
 *
 * @param {array} places [{ id, name, meters }] (see placesOf)
 * @param {object|null} place The one picked
 * @param {function} onPick Gets the place picked
 */
export default function PlacePicker({ places, place, onPick, disabled }) {
    const intl = useIntl();
    const dropdown = useRef();
    const list = useRef();
    const [text, setText] = useState("");
    const found = useMemo(() => placesNamed(places, text).slice(0, SHOWN), [places, text]);

    // The next time it opens, the list starts from its first place: it is set back while still in sight, on closing
    useEffect(() => {
        const opened = dropdown.current;
        const toTop = () => {
            if (list.current) list.current.scrollTop = 0;
        };
        opened.addEventListener("sl-hide", toTop);
        return () => opened.removeEventListener("sl-hide", toTop);
    }, []);

    const pick = (item) => {
        onPick(item);
        setText("");
        dropdown.current && dropdown.current.hide();
    };

    return (
        <sl-dropdown ref={dropdown} placement="bottom-start" hoist>
            <button slot="trigger" type="button" className="pill pill--outline pill--caret" disabled={disabled}>
                { place ? place.name : <FormattedMessage id="app.messages.choosePlace" defaultMessage="Choose place" /> }
            </button>
            <div className="popoverPanel messagePicker__panel">
                <SlInput
                    size="small"
                    value={text}
                    autocomplete="off"
                    placeholder={intl.formatMessage({ id: "app.messages.findPlace", defaultMessage: "Find a place" })}
                    onSlInput={(event) => setText(event.target.value)}
                />
                <div className="messagePicker__options" ref={list}>
                    { found.map((item) =>
                        <button key={item.id} type="button" className="popoverPanel__option messagePicker__place" onClick={() => pick(item)}>
                            <span>{item.name || <FormattedMessage id="app.messages.placeWithoutName" defaultMessage="Place without name" />}</span>
                            { item.meters !== null && <span className="messagePicker__distance"><Distance meters={item.meters} /></span> }
                        </button>
                    )}
                    { found.length === 0 &&
                        <p className="messagePicker__empty">
                            <FormattedMessage id="app.messages.noPlaces" defaultMessage="No place of the map has that name." />
                        </p>
                    }
                </div>
            </div>
        </sl-dropdown>
    );
}
