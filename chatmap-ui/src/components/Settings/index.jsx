function Settings() {
    return (
        <div className="settings">
            <h2>Map settings</h2>
            <h3>Link content to locations</h3>
            <div className="settingsOptions">
                <div className="option">
                    <sl-checkbox size="small" checked>Image</sl-checkbox>
                </div>
                <div className="option">
                    <sl-checkbox size="small" checked>Video</sl-checkbox>
                </div>
                <div className="option">
                    <sl-checkbox size="small" checked>Audio</sl-checkbox>
                </div>
                <div className="option">
                    <sl-checkbox size="small" >Text</sl-checkbox>
                </div>
            </div>
            <h3>Moderation</h3>
            <div className="settingsOptions">
                <sl-radio-group label="Select an option" name="a" value="1">
                    <div className="option">
                        <sl-radio size="small" checked value="1">All messages</sl-radio>
                    </div>
                    <div className="option">
                        <sl-radio size="small" value="2">Selected messages</sl-radio>
                    </div>
                </sl-radio-group>
            </div>
            <hr />
             <div className="settingsOptions">
                <sl-button size="small">Save & apply</sl-button>
             </div>
        </div>
    )
}

export default Settings;


