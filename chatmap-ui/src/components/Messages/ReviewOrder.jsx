import { FormattedMessage, useIntl } from "react-intl";

import { MARKED } from "./order.js";
import "./reviewOrder.css";

// Between the two stretches of the messages (see order.js): the older ones go under it
export function BeforeReviewed() {
    return (
        <h3 className="reviewOrder__separator">
            <span>
                <FormattedMessage id="app.messages.beforeReviewed" defaultMessage="Older than the last reviewed of its group" />
            </span>
        </h3>
    );
}

// On a message a rule marked, shown first for it
export function MarkedFirst({ message }) {
    const intl = useIntl();
    if (message.rank !== MARKED) return null;
    const label = intl.formatMessage({ id: "app.messages.markedFirst", defaultMessage: "It suggests something: shown first" });
    return <span className="reviewOrder__marked" role="img" aria-label={label} title={label}>★</span>;
}
