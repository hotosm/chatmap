import { FormattedMessage, useIntl } from "react-intl";

import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';
import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";
import "@shoelace-style/shoelace/dist/components/visually-hidden/visually-hidden.js";

import { colorKeys } from "./tags.js";

/**
 * Which key colors the points of the map, for whoever looks at it, as a pill
 * like "Add point". It starts with the one its owner chose; changing it here
 * is not saved.
 */
export default function ColorBy({ keys, colorKey, onChange }) {
    const intl = useIntl();
    const options = colorKeys(keys);
    if (options.length === 0) return null;

    const current = options.find((key) => key.id === colorKey);
    // The chosen one with a check; drawn here so it always says what the map shows
    const choice = (keyId, label) =>
        <sl-menu-item key={keyId || "none"} onClick={() => onChange(keyId)}>
            <span slot="prefix" className="colorBy__check" aria-hidden="true">{(colorKey || null) === keyId ? "✓" : ""}</span>
            {label}
            { (colorKey || null) === keyId &&
                <sl-visually-hidden>
                    {" "}<FormattedMessage id="app.tags.chosen" defaultMessage="(chosen)" />
                </sl-visually-hidden>
            }
        </sl-menu-item>;

    return (
        <sl-dropdown className="colorBy" hoist>
            <SlButton slot="trigger" pill caret title={intl.formatMessage({ id: "app.tags.colorBy", defaultMessage: "Color by" })}>
                <SlIcon name="palette" slot="prefix" />
                { current ?
                    <FormattedMessage id="app.tags.coloredBy" defaultMessage="Color: {key}" values={{ key: current.key }} /> :
                    <FormattedMessage id="app.tags.colorBy" defaultMessage="Color by" />
                }
            </SlButton>
            <sl-menu>
                { options.map((key) => choice(key.id, key.key)) }
                { choice(null, intl.formatMessage({ id: "app.tags.colorByNone", defaultMessage: "Nothing" })) }
            </sl-menu>
        </sl-dropdown>
    );
}
