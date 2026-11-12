import { useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";
import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";

import { MAX_GROUP_PLACES, groupPlaces, placesToAdd } from "./messages.js";

/**
 * The places a chat group is always about, in its row of the groups: an
 * option, closed until it is asked for, for a group sure to speak of one or
 * two places only (the observers of a checkpoint). A group without places
 * works as any other.
 *
 * @param {object} group { id, point_ids }
 * @param {array} places The places of the map (see placesOf)
 * @param {function} onSave Gets the point ids to keep; answers whether they were saved
 */
export default function GroupPlaces({ group, places, busy, onSave }) {
    const intl = useIntl();
    const chosen = groupPlaces(group, places);
    const [open, setOpen] = useState(false);
    const [text, setText] = useState("");
    const found = placesToAdd(places, chosen.map((place) => place.id), text);

    const save = (pointIds) => onSave(pointIds).then((saved) => saved && setText(""));

    if (!open && chosen.length === 0) {
        return (
            <button type="button" className="groupsPicker__cancel groupPlaces__ask" onClick={() => setOpen(true)}>
                <FormattedMessage id="app.messages.groupPlacesAsk" defaultMessage="This group always speaks of…" />
            </button>
        );
    }

    return (
        <div className="groupPlaces">
            <p className="groupPlaces__help">
                <FormattedMessage
                    id="app.messages.groupPlacesHelp"
                    defaultMessage="Only if you are sure: its messages come with this place chosen, and you can change it."
                />
            </p>
            { chosen.length > 0 &&
                <ul className="groupPlaces__chosen">
                    { chosen.map((place) =>
                        <li key={place.id} className="pill pill--outline groupPlaces__place">
                            <span>{place.name || <FormattedMessage id="app.messages.placeWithoutName" defaultMessage="Place without name" />}</span>
                            <button
                                type="button"
                                className="groupPlaces__remove"
                                disabled={busy}
                                aria-label={intl.formatMessage({ id: "app.messages.groupPlacesRemove", defaultMessage: "Remove this place" })}
                                onClick={() => save(chosen.filter((item) => item.id !== place.id).map((item) => item.id))}
                            >
                                <SlIcon name="x-lg" />
                            </button>
                        </li>
                    )}
                </ul>
            }
            { chosen.length < MAX_GROUP_PLACES ?
                <>
                    <SlInput
                        size="small"
                        value={text}
                        autocomplete="off"
                        disabled={busy}
                        placeholder={intl.formatMessage({ id: "app.messages.findPlace", defaultMessage: "Find a place" })}
                        onSlInput={(event) => setText(event.target.value)}
                    />
                    { text.trim() &&
                        <div className="groupPlaces__found">
                            { found.map((place) =>
                                <button
                                    key={place.id}
                                    type="button"
                                    className="popoverPanel__option"
                                    disabled={busy}
                                    onClick={() => save([...chosen.map((item) => item.id), place.id])}
                                >
                                    {place.name || <FormattedMessage id="app.messages.placeWithoutName" defaultMessage="Place without name" />}
                                </button>
                            )}
                            { found.length === 0 &&
                                <p className="groupPlaces__help">
                                    <FormattedMessage id="app.messages.noPlaces" defaultMessage="No place of the map has that name." />
                                </p>
                            }
                        </div>
                    }
                </> :
                <p className="groupPlaces__help">
                    <FormattedMessage
                        id="app.messages.groupPlacesFull"
                        defaultMessage="{max, plural, one {A group speaks of # place at most.} other {A group speaks of # places at most.}}"
                        values={{ max: MAX_GROUP_PLACES }}
                    />
                </p>
            }
            { chosen.length === 0 &&
                <button type="button" className="groupsPicker__cancel" onClick={() => { setOpen(false); setText(""); }}>
                    <FormattedMessage id="app.dialog.confirm.cancel" defaultMessage="Cancel" />
                </button>
            }
        </div>
    );
}
