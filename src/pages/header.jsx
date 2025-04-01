import React, { useState, useEffect } from 'react';
import logo from '../assets/hot-logo.svg';
import SaveButton from '../components/SaveButton/index.jsx';
import NavBar from '../components/NavBar';
import NavModal from '../components/NavModal';
import Settings from "../components/Settings/index.jsx";
import { FormattedMessage } from 'react-intl';

export default function Header({
    dataAvailable,
    dataFiles,
    mapData,
    handleNewUploadClick,
    settings,
    handleSettingsChange
}) {

    // Store for the modal window content
    const [modalContent, setModalContent] = useState(null);

    // The modal has been closed
    const handleModalClose = () => {
        setModalContent(null);
    }
    // If this settings option has change, close the modal window
    useEffect(() => {
        setModalContent(null);
    }, [settings.msgPosition])

    return (
        <>

        <header className="header">

            {/* Navigation var */}
            <div className="top">
            {!dataAvailable &&
            <NavBar onOptionClick={(option) => {
                if (option === "options") {
                    // Display settings as a modal
                    setModalContent(<Settings settings={settings} onChange={handleSettingsChange} />)
                }
            }} />
            }
            <NavModal isOpen={modalContent !== null} onClose={handleModalClose} content={modalContent} />
            </div>

            {/* Logo */}
            <h1 className={dataAvailable ? "titleSmall" : "title"} >
            <img src={logo} className="logo" alt="logo" />
            <span>ChatMap</span>
            </h1>

            {/* Options: upload new file, download */}
            { dataAvailable ?
            <div className="fileOptions">
                <SaveButton data={mapData} dataFiles={dataFiles} />
                <button onClick={handleNewUploadClick} className="secondaryButton">
                <FormattedMessage
                    id = "app.uploadNewFile"
                    defaultMessage="Upload new file"
                /> 
                </button>
            </div>
            :
            <>
            {/* Main legend */}
            <p className="subtitle">
                <FormattedMessage
                id = "app.subtitle"
                defaultMessage="Export and upload a chat to visualize locations, messages and media"
                />
            </p>
            <p className="highlighted">
                <FormattedMessage
                id = "app.supportedApps"
                defaultMessage="Now it works with WhatsApp, Telegram or Signal!"
                />
            </p>
            </>
            }
        </header>
    </>
    );
}