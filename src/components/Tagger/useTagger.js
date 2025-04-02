import { useState } from 'react';

/**
 * Hook for managing tags
 *
 *  It will keep the state for settings, barely used for now
 */
function useTagger() {

    const [allTags, setAllTags] = useState({});

    const add = (id, key, value) => {
        return setAllTags(prev => ({
            ...prev,
            [id]: {
                ...prev[id],
                [key]: value
            }
        }));
    }

    const remove = (id, key) => {
        return setAllTags(prev => {
            const newTags = { ...prev };
            delete newTags[id][key];
            return newTags;
        });
    }

    const tags = (id) => {
        return allTags[id];
    }

    return [add, remove, tags];

}

export default useTagger;
