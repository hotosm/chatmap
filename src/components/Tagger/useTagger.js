import { useState } from 'react';

/**
 * Hook for managing tags
 *
 *  It will keep the state for settings, barely used for now
 */
function useTagger() {

    const [tags, setTags] = useState({});

    const addTag = (key, value) => {
        setTags(prev => ({...prev, [key]: value}));
    }

    return [tags, addTag];

}

export default useTagger;
