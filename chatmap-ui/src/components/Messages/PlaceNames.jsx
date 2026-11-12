import { useEffect, useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import { Values } from "./ConditionGroup.jsx";
import { CONTAINS, CONTENT } from "./rules.js";
import useMessagesApi from "./useMessagesApi.js";

// As the API takes them
export const MAX_PLACE_NAMES = 20;
export const MAX_PLACE_NAME_LENGTH = 100;

/**
 * The other names of a place, as the chats write it ("el puente viejo",
 * "عين الريحان"), as pills: a line of a message that says one of them names
 * the place, and what it says is suggested for it. Each change is saved.
 */
export default function PlaceNames({ pointId }) {
    const intl = useIntl();
    const { readPlaceNames, updatePlaceNames } = useMessagesApi();
    const [names, setNames] = useState(null);
    const [failed, setFailed] = useState(false);

    useEffect(() => {
        const current = { on: true };
        setNames(null);
        readPlaceNames(pointId).then((read) => {
            if (!current.on) return;
            setFailed(!read);
            setNames(read ? read.names : []);
        });
        return () => { current.on = false; };
    }, [pointId, readPlaceNames]);

    if (names === null) return null;

    const save = async (changed) => {
        const before = names;
        setNames(changed);
        const saved = await updatePlaceNames(pointId, changed);
        setFailed(!saved);
        setNames(saved ? saved.names : before);
    };

    return (
        <section className="placeNames">
            <h3 className="pointMessages__subtitle">
                <FormattedMessage id="app.placeNames.title" defaultMessage="Other names" />
            </h3>
            <Values
                condition={{ field: CONTENT, operator: CONTAINS, values: names }}
                groups={[]}
                max={MAX_PLACE_NAMES}
                maxLength={MAX_PLACE_NAME_LENGTH}
                placeholder={intl.formatMessage({ id: "app.placeNames.placeholder", defaultMessage: "e.g. the old bridge, then Enter" })}
                onChange={(condition) => save(condition.values)}
            />
            <p className="placeNames__help">
                <FormattedMessage
                    id="app.placeNames.help"
                    defaultMessage="As the chats write it, in any language. A line that says one of them speaks of this place."
                />
            </p>
            { failed &&
                <p className="messageLinker__notice messageLinker__notice--error" role="alert">
                    <FormattedMessage id="app.messages.notSaved" defaultMessage="It could not be saved. Try again." />
                </p>
            }
        </section>
    );
}
