import { useCallback } from "react";
import { useIntl } from "react-intl";

// The name of a group to show, also for a group the phone gives without one
export default function useGroupName() {
    const intl = useIntl();
    return useCallback(
        (name) => name || intl.formatMessage({ id: "app.messages.groupWithoutName", defaultMessage: "Group without a name" }),
        [intl],
    );
}
