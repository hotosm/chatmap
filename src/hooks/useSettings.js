import { useState } from 'react';

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
