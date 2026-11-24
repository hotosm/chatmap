import { useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlButton from "@shoelace-style/shoelace/dist/react/button/index.js";
import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";
import SlIconButton from "@shoelace-style/shoelace/dist/react/icon-button/index.js";
import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";

import { cleanName, placeName, placeNamed, reportOrigin } from "./tags.js";

/**
 * The name of a point of the map, and the way to change it. A place shows
 * its name; a report (from the app or a chat) says it has none, and naming
 * it makes it a place. Two places of a map do not have the same name.
 *
 * @param {object} props.properties The point, as the map has it
 * @param {array} props.features The points of the map, to tell a name taken
 * @param {boolean} props.canEdit Whether the person can name it
 * @param {function} props.namePoint Saves a name (see useTagsApi). Passed in, not taken from
 *   the context: the popup of the map is drawn apart from the app and has none
 * @param {function} props.onNamed Takes the properties of the point with its new name
 * @param {boolean} props.withName False where the name is shown already (the title of a sheet)
 * @param {string} props.heading The level of its title: "h3" in a popup, "h2" in a panel
 */
export default function PlaceTitle({
    properties, features, canEdit, namePoint, onNamed, withName = true, heading = "h3",
}) {
    const intl = useIntl();
    const [editing, setEditing] = useState(false);
    const [name, setName] = useState("");
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);

    const current = placeName({ properties });
    const origin = reportOrigin(properties);
    const Heading = heading;

    const start = () => {
        setName(current);
        setError(null);
        setEditing(true);
    };
    const cancel = () => {
        setEditing(false);
        setError(null);
    };
    const taken = (other) => intl.formatMessage(
        { id: "app.placeName.taken", defaultMessage: "There is a place with that name already: «{name}»." },
        { name: other },
    );

    async function save(event) {
        event.preventDefault();
        const chosen = cleanName(name);
        if (!chosen) return;
        if (chosen === current) {
            cancel();
            return;
        }
        // Each place has a name of its own; its own name written another way is still its own
        const other = placeNamed(features, chosen, properties.id);
        if (other) {
            setError(taken(placeName(other)));
            return;
        }
        setSaving(true);
        const { status, answer } = await namePoint(properties.id, chosen);
        setSaving(false);
        if (!answer) {
            setError(status === 409 ? taken(chosen) : intl.formatMessage({
                id: "app.placeName.error", defaultMessage: "The name could not be saved. Try again.",
            }));
            return;
        }
        setEditing(false);
        onNamed && onNamed({ ...properties, name: answer.name, place: true });
    }

    const kind = origin &&
        <span className="placeTitle__kind">
            <SlIcon name={origin === "app" ? "phone" : "chat-dots"} />
            { origin === "app" ?
                <FormattedMessage id="app.placeName.fromApp" defaultMessage="Report · from the app" /> :
                <FormattedMessage id="app.placeName.fromChat" defaultMessage="Report · from a chat" />
            }
        </span>;

    if (editing) {
        return (
            <div className="placeTitle">
                {kind}
                {/* Typing here does not move the map; Escape gives up */}
                <form
                    className="placeTitle__form"
                    onSubmit={save}
                    onKeyDown={(event) => {
                        event.stopPropagation();
                        if (event.key === "Escape") cancel();
                    }}
                >
                    <SlInput
                        autofocus
                        size="small"
                        value={name}
                        maxlength={100}
                        className={error ? "placeTitle__input placeTitle__input--error" : "placeTitle__input"}
                        aria-label={intl.formatMessage({ id: "app.tags.addPoint.nameLabel", defaultMessage: "Name" })}
                        placeholder={intl.formatMessage({ id: "app.tags.addPoint.name", defaultMessage: "Ex: South access" })}
                        onSlInput={(event) => {
                            setName(event.target.value);
                            setError(null);
                        }}
                    />
                    { error &&
                        <p className="placeTitle__error" role="alert">
                            <SlIcon name="exclamation-circle" />
                            {error}
                        </p>
                    }
                    <p className="placeTitle__help">
                        { properties.place ?
                            <FormattedMessage
                                id="app.placeName.helpRename"
                                defaultMessage="The name also tells the place in the messages."
                            /> :
                            <FormattedMessage
                                id="app.placeName.helpReport"
                                defaultMessage="It becomes a place of the map: it can have statuses and messages linked. The photo, who sent it and what it said stay."
                            />
                        }
                    </p>
                    <div className="placeTitle__buttons">
                        <SlButton size="small" type="submit" variant="primary" className="dark-btn" loading={saving}>
                            { properties.place ?
                                <FormattedMessage id="app.placeName.save" defaultMessage="Save" /> :
                                <FormattedMessage id="app.placeName.saveAsPlace" defaultMessage="Save as a place" />
                            }
                        </SlButton>
                        <SlButton size="small" variant="text" disabled={saving} onClick={cancel}>
                            <FormattedMessage id="app.dialog.confirm.cancel" defaultMessage="Cancel" />
                        </SlButton>
                    </div>
                </form>
            </div>
        );
    }

    const rename = intl.formatMessage({ id: "app.placeName.rename", defaultMessage: "Change the name" });
    return (
        <div className="placeTitle">
            {kind}
            <div className="placeTitle__row">
                { withName &&
                    <Heading className={current ? "placeTitle__name" : "placeTitle__name placeTitle__name--none"}>
                        { current || <FormattedMessage id="app.placeName.none" defaultMessage="No name" /> }
                    </Heading>
                }
                { canEdit && namePoint && properties.place && (withName ?
                    <SlIconButton name="pencil" label={rename} onClick={start} /> :
                    <SlButton size="small" variant="text" onClick={start}>
                        <SlIcon slot="prefix" name="pencil" />
                        {rename}
                    </SlButton>
                )}
            </div>
            { canEdit && namePoint && !properties.place &&
                <SlButton size="small" outline className="placeTitle__give" onClick={start}>
                    <SlIcon slot="prefix" name="pin-map" />
                    <FormattedMessage id="app.placeName.give" defaultMessage="Give it a name" />
                </SlButton>
            }
        </div>
    );
}
