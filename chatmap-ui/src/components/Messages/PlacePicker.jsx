import { useEffect, useMemo, useRef, useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";
import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";

import BottomSheet from "../BottomSheet";
import { timeAgo } from "../TimeAgo";
import usePhone from "../BottomSheet/usePhone.js";
import { ValueChip } from "../Tags";
import { Distance } from "./MessageCard.jsx";
import PlaceMap from "./PlaceMap.jsx";
import { newPlaceName, placesCoords, statusOf } from "./linkStates.js";
import { placesNamed } from "./messages.js";
import { sameName } from "../Tags/tags.js";
import "./linkStates.css";

// How many places the panel lists at once: the rest are found by name
const SHOWN = 30;

// What a place shows now for the key of the map, next to its name. An expired value says what it was, faded
function Status({ status }) {
    const intl = useIntl();
    if (!status) return null;
    if (!status.unknown) return <ValueChip value={status} className="placePicker__status" />;
    const expired = <FormattedMessage id="app.messages.expiredStatus" defaultMessage="Expired" />;
    if (!status.last) return <span className="pill placePicker__status placePicker__status--expired">{expired}</span>;
    const ago = status.expiredAt && timeAgo(status.expiredAt);
    const title = intl.formatMessage(
        { id: "app.messages.expiredSince", defaultMessage: "{value}, expired {ago}: nobody confirmed it since" },
        { value: status.last.value, ago: ago ? intl.formatRelativeTime(ago.value, ago.unit, { numeric: "auto" }) : "" },
    );
    return (
        <span className="placePicker__expired" title={title}>
            <ValueChip value={status.last} className="placePicker__status placePicker__status--faded" />
            <span className="placePicker__expiredLabel">{expired}</span>
        </span>
    );
}

// [lat, lon] of a point of the map
const coordsOfFeature = (feature) => feature ? [feature.geometry.coordinates[1], feature.geometry.coordinates[0]] : null;

/**
 * A pill to pick a place of the map, in a panel: found by its name, with
 * what each one shows now for the key of the map, and nearest first when
 * the message says where it was sent from. Then a small map shows that
 * location and the place in sight (the nearest, or the one pointed at), and
 * a new place can be created there: with what was looked for as its name,
 * when no place has it, or with a name written for it.
 *
 * On a phone the panel takes the width of the screen; a sheet from the
 * bottom (BottomSheet) will take its place there.
 *
 * @param {array} places [{ id, name, meters }] (see placesOf)
 * @param {object|null} place The one picked
 * @param {function} onPick Gets the place picked
 * @param {array|null} coords [lat, lon] of the message, if it says
 * @param {array} features The points of the map, to show them
 * @param {object|null} statusKey The key whose value each place shows (see statusKeyOf)
 * @param {function|null} onCreate Gets a name and [lat, lon] and creates a place there: where the
 *   message was sent from or, when it does not say, where it is pointed on the small map. Answers
 *   the place, or null when it is not created. Without it, no place is created here
 */
export default function PlacePicker({ places, place, onPick, disabled, coords, features, statusKey, onCreate }) {
    const intl = useIntl();
    const phone = usePhone();
    const dropdown = useRef();
    const list = useRef();
    const [text, setText] = useState("");
    // The panel is open: the small map is only made then
    const [open, setOpen] = useState(false);
    // The place pointed at in the list, shown on the small map
    const [pointed, setPointed] = useState(null);
    // The name of a new place being written, or null
    const [naming, setNaming] = useState(null);
    const [creating, setCreating] = useState(false);
    const [notCreated, setNotCreated] = useState(false);
    // The place that already has the name asked for a new one
    const [taken, setTaken] = useState(null);
    // Where a new place goes when the message does not say where it was sent from: pointed on the small map
    const [at, setAt] = useState(null);
    const around = useMemo(() => placesCoords(features), [features]);
    const found = useMemo(() => placesNamed(places, text).slice(0, SHOWN), [places, text]);
    const byId = useMemo(
        () => new Map((features || []).map((feature) => [feature.properties.id, feature])), [features],
    );

    // Closing it leaves it as new: the list from its first place, nothing being written
    const closed = () => {
        if (list.current) list.current.scrollTop = 0;
        setOpen(false);
        setPointed(null);
        setNaming(null);
        setNotCreated(false);
        setAt(null);
    };

    // On a computer it is a dropdown; on a phone, a sheet from the bottom (below)
    useEffect(() => {
        const panel = dropdown.current;
        if (!panel) return;
        const shown = (event) => event.target === panel && setOpen(true);
        const hidden = (event) => event.target === panel && closed();
        panel.addEventListener("sl-after-show", shown);
        panel.addEventListener("sl-after-hide", hidden);
        return () => {
            panel.removeEventListener("sl-after-show", shown);
            panel.removeEventListener("sl-after-hide", hidden);
        };
    }, [phone]);

    const pick = (item) => {
        onPick(item);
        setText("");
        dropdown.current && dropdown.current.hide();
        if (phone) closed();
    };

    const where = coords || at;
    const create = async (name) => {
        if (!name || !where || creating) return;
        setNotCreated(false);
        // Each place has a name of its own: the one that has it is in the list, to choose it
        const named = places.find((item) => sameName(item.name) === sameName(name));
        setTaken(named || null);
        if (named) return;
        setCreating(true);
        const created = await onCreate(name, where);
        setCreating(false);
        if (created) pick(created);
        else setNotCreated(true);
    };

    const asked = newPlaceName(text);
    // On the small map: the place pointed at, or else the nearest
    const inSight = pointed || (coords && found[0]) || null;
    // Choosing where a new place goes, on the small map
    const choosing = naming !== null && !coords;
    const nameOf = (item) => item.name ||
        intl.formatMessage({ id: "app.messages.placeWithoutName", defaultMessage: "Place without name" });

    const title = <FormattedMessage id="app.messages.choosePlace" defaultMessage="Choose place" />;
    const trigger = (slot) =>
        <button
            slot={slot}
            type="button"
            className="pill pill--outline pill--caret"
            disabled={disabled}
            onClick={slot ? undefined : () => setOpen(true)}
        >
            { place ? place.name : title }
        </button>;
    const panel =
            <div className={`popoverPanel messagePicker__panel placePicker ${coords || choosing ? "placePicker--withMap" : ""}`}>
                { !phone && <h3 className="placePicker__title">{title}</h3> }
                <div className="placePicker__body">
                    <div className="placePicker__list">
                        <SlInput
                            size="small"
                            value={text}
                            autocomplete="off"
                            placeholder={intl.formatMessage({ id: "app.messages.findPlace", defaultMessage: "Find a place" })}
                            onSlInput={(event) => setText(event.target.value)}
                        />
                        { coords && !asked && found.length > 0 &&
                            <div className="popoverPanel__title">
                                <FormattedMessage id="app.messages.nearest" defaultMessage="Nearest to the shared location" />
                            </div>
                        }
                        <div className="messagePicker__options" ref={list} onMouseLeave={() => setPointed(null)}>
                            { found.map((item) =>
                                <button
                                    key={item.id}
                                    type="button"
                                    className="popoverPanel__option messagePicker__place"
                                    onClick={() => pick(item)}
                                    onMouseEnter={() => setPointed(item)}
                                    onFocus={() => setPointed(item)}
                                >
                                    <span className="placePicker__name">
                                        <span>{nameOf(item)}</span>
                                        <Status status={statusOf(byId.get(item.id), statusKey)} />
                                    </span>
                                    { item.meters !== null && <span className="messagePicker__distance"><Distance meters={item.meters} /></span> }
                                </button>
                            )}
                            { found.length === 0 &&
                                <p className="messagePicker__empty">
                                    <FormattedMessage id="app.messages.noPlaces" defaultMessage="No place of the map has that name." />
                                </p>
                            }
                        </div>
                        { onCreate && naming === null &&
                            <div className="placePicker__create">
                                { asked && found.length === 0 ?
                                    <button
                                        type="button"
                                        className="placePicker__createButton"
                                        disabled={creating}
                                        onClick={() => coords ? create(asked) : setNaming(asked)}
                                    >
                                        <SlIcon name="plus-lg" />
                                        <FormattedMessage id="app.messages.createNamed" defaultMessage="Create “{name}”" values={{ name: asked }} />
                                    </button> :
                                    <button type="button" className="placePicker__createButton" onClick={() => setNaming(asked || "")}>
                                        <SlIcon name="plus-lg" />
                                        { coords ?
                                            <FormattedMessage id="app.messages.createHere" defaultMessage="Create a new place at this location" /> :
                                            <FormattedMessage id="app.messages.createPointed" defaultMessage="Create a new place, pointing where it is" />
                                        }
                                    </button>
                                }
                            </div>
                        }
                        { onCreate && naming !== null &&
                            <form
                                className="placePicker__naming"
                                onSubmit={(event) => { event.preventDefault(); create(newPlaceName(naming)); }}
                            >
                                <SlInput
                                    size="small"
                                    value={naming}
                                    autofocus
                                    autocomplete="off"
                                    label={intl.formatMessage({ id: "app.messages.newPlaceName", defaultMessage: "Name of the new place" })}
                                    onSlInput={(event) => setNaming(event.target.value)}
                                />
                                <div className="placePicker__namingButtons">
                                    <button type="button" className="pill pill--outline" disabled={creating} onClick={() => setNaming(null)}>
                                        <FormattedMessage id="app.dialog.confirm.cancel" defaultMessage="Cancel" />
                                    </button>
                                    <button type="submit" className="pill" disabled={creating || !newPlaceName(naming) || !where}>
                                        <FormattedMessage id="app.messages.create" defaultMessage="Create" />
                                    </button>
                                </div>
                            </form>
                        }
                        { taken &&
                            <p className="messageLinker__notice messageLinker__notice--error" role="alert">
                                <FormattedMessage
                                    id="app.messages.nameTaken"
                                    defaultMessage="“{name}” is a place already: choose it in the list."
                                    values={{ name: <bdi>{taken.name}</bdi> }}
                                />
                            </p>
                        }
                        { notCreated &&
                            <p className="messageLinker__notice messageLinker__notice--error" role="alert">
                                <FormattedMessage id="app.messages.notCreated" defaultMessage="The place could not be created. Try again." />
                            </p>
                        }
                    </div>
                    { choosing &&
                        <figure className="placePicker__map">
                            <PlaceMap around={around} place={at} onPoint={setAt} />
                            <figcaption className="placePicker__caption">
                                <SlIcon name="geo-alt" />
                                <span>
                                    { at ?
                                        <FormattedMessage id="app.messages.pointedHere" defaultMessage="The new place goes here. Click again to move it." /> :
                                        <FormattedMessage id="app.messages.pointWhere" defaultMessage="Click on the map where the place is." />
                                    }
                                </span>
                            </figcaption>
                        </figure>
                    }
                    { coords &&
                        <figure className="placePicker__map">
                            { open && <PlaceMap from={coords} place={coordsOfFeature(inSight && byId.get(inSight.id))} /> }
                            <figcaption className="placePicker__caption">
                                <SlIcon name="geo-alt" />
                                <span>
                                    { inSight && inSight.meters !== null ?
                                        <FormattedMessage
                                            id="app.messages.sharedNear"
                                            defaultMessage="Shared location · {place} at {distance}"
                                            values={{ place: <strong>{nameOf(inSight)}</strong>, distance: <Distance meters={inSight.meters} /> }}
                                        /> :
                                        <FormattedMessage id="app.messages.sharedLocation" defaultMessage="Shared location" />
                                    }
                                </span>
                            </figcaption>
                        </figure>
                    }
                </div>
            </div>;

    return phone ?
        <>
            {trigger()}
            <BottomSheet open={open} title={title} onClose={closed} snaps={["half", "full"]} initialSnap="full" modalAt="half" className="placePicker--sheet">
                {open && panel}
            </BottomSheet>
        </> :
        <sl-dropdown ref={dropdown} placement="bottom-start" hoist>
            {trigger("trigger")}
            {panel}
        </sl-dropdown>;
}
