import { useCallback, useEffect, useState } from "react";

import { useConfigContext } from "../../context/ConfigContext.jsx";
import { apiV2, request, send } from "../../utils/apiV2.js";

/**
 * The rules of a map while they are open: read once, and saved one by one.
 * Each change answers the rule (or the rules) saved, or null when the API
 * does not take it; the list only changes when it does.
 *
 * @returns {object} { rules (null while read), failed, create, update, remove, order }
 */
export default function useRules(mapId) {
    const { config } = useConfigContext();
    const api = apiV2(config.API_URL);
    const [rules, setRules] = useState(null);
    const [failed, setFailed] = useState(false);

    useEffect(() => {
        let current = true;
        setRules(null);
        request(`${api}/maps/${mapId}/rules`).then((answer) => {
            if (!current) return;
            setFailed(!answer);
            setRules(answer ? answer.rules : []);
        });
        return () => { current = false; };
    }, [api, mapId]);

    const create = useCallback(async (rule) => {
        const saved = await send('POST', `${api}/maps/${mapId}/rules`, rule);
        if (saved) setRules((shown) => [...shown, saved]);
        return saved;
    }, [api, mapId]);

    const update = useCallback(async (ruleId, rule) => {
        const saved = await send('PUT', `${api}/maps/${mapId}/rules/${ruleId}`, rule);
        if (saved) setRules((shown) => shown.map((item) => item.id === ruleId ? saved : item));
        return saved;
    }, [api, mapId]);

    const remove = useCallback(async (ruleId) => {
        const removed = await send('DELETE', `${api}/maps/${mapId}/rules/${ruleId}`);
        if (removed) setRules((shown) => shown.filter((item) => item.id !== ruleId));
        return removed;
    }, [api, mapId]);

    return { rules, failed, create, update, remove };
}
