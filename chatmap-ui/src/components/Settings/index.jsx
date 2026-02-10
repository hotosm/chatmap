import { useState, useEffect } from 'react';

function Settings({
    handleCloseClick,
}) {

    const [settings, setSettings] = useState({
        types: {
            all: true,
            media: false,
            text: false
        },
        moderation: {
            all: true,
            filtered: false
        }
    })

    const handleSelectSetting = (category, key) => {
        setSettings(prevSettings => {
            const newSettings = {...prevSettings[category]}
            for (let setting in newSettings) {
                if (setting === key) {
                    newSettings[setting] = true;
                } else {
                    newSettings[setting] = false;
                }
            }
            return {...prevSettings, [category]: {...newSettings}};
        })
    }

    // useEffect(() => {
    //     console.log(settings)
    // }, [settings]);

    return (
        <div className="settings">
            <sl-icon-button
                name="x-lg"
                className="closeButton"
                onClick={handleCloseClick}
            ></sl-icon-button>
            <h2>Map settings</h2>
            <h3>Link messages to locations</h3>
            <div className="settingsOptions">
                <div className="option">
                    <sl-radio
                        onClick={() => handleSelectSetting("types", "all")}
                        checked={settings.types.all}
                        size="small"
                    >
                        Text and media
                    </sl-radio>
                </div>
                <div className="option">
                    <sl-radio
                        onClick={() => handleSelectSetting("types", "media")}
                        checked={settings.types.media}
                        size="small"
                    >
                        Media only
                </sl-radio>
                </div>
                <div className="option">
                    <sl-radio
                        onClick={() => handleSelectSetting("types", "text")}
                        checked={settings.types.text}
                        size="small"
                    >
                        Text only
                    </sl-radio>
                </div>
            </div>
            <h3>Moderation</h3>
            <div className="settingsOptions">
                    <div className="option">
                        <sl-radio 
                            size="small"
                            checked={settings.moderation.all}
                            onClick={() => handleSelectSetting("moderation", "all")}
                        >
                            All messages
                        </sl-radio>
                    </div>
                    <div className="option">
                        <sl-radio 
                            size="small"
                            checked={settings.moderation.filtered}
                            onClick={() => handleSelectSetting("moderation", "filtered")}
                        >
                            Filtered
                        </sl-radio> 
                    </div>
                <div className="option">
                    <sl-button
                        size="small"
                        disabled={!settings.moderation.filtered}
                    >
                        Select groups
                    </sl-button>
                    &nbsp;
                    <sl-button
                        size="small"
                        disabled={!settings.moderation.filtered}
                    >
                        Select contacts
                    </sl-button>
                </div>
            </div>
            <hr />
             <div className="settingsOptions">
                <sl-button variant="success" size="small">
                    <strong>Save & apply</strong>
                </sl-button>
             </div>
        </div>
    )
}

export default Settings;


