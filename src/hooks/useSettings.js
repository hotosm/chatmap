import { useState } from 'react';

/**
 * Hook for managing settings
 *
 *  It will keep the state for settings, barely used for now
 */
function useSettings(initialSettings) {

    const [settings, setSettings] = useState(initialSettings);

    const handleSettingsChange = (settings) => {
        setSettings(settings);
    }

    const resetSettings = () => {
        setSettings(initialSettings);
    }

    return [settings, handleSettingsChange, resetSettings];

}

export default useSettings;
