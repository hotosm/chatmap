import { FormattedMessage } from "react-intl";

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
