import { useCallback, useState } from "react";

import useMessagePages from "./useMessagePages.js";
import usePhoneGroups from "./usePhoneGroups.js";
import { groupNames } from "./messages.js";

/**
 * The messages of a map while its page is open, with the groups they come
 * from: the groups of its phone (usePhoneGroups) and the messages of the
 * one read, or of all of them, in the state asked for (useMessagePages).
 *
 * @param {string} mapId The map
 */
export default function useMessages(mapId) {
    const [phone, setPhone] = usePhoneGroups(mapId);
    const [groupId, setGroupId] = useState(null);
    const [state, setState] = useState(null);
    const pages = useMessagePages(mapId, groupId, state);
    const { reload } = pages;

    // After a group changes: the one read can no longer be, and the messages are read again
    const changed = useCallback((answer) => {
        setPhone(answer);
        if (groupId && !answer.groups.some((group) => group.id === groupId && group.enabled)) setGroupId(null);
        reload();
    }, [groupId, setPhone, reload]);

    const groups = phone && phone.groups;
    return { phone, changed, groups, names: groupNames(groups), groupId, setGroupId, state, setState, ...pages };
}
