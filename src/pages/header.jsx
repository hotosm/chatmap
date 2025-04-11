import React from 'react';
import logo from '../assets/hot-logo.svg';
import SaveButton from '../components/SaveButton/index.jsx';
import TagsOptions from "../components/TagsOptions";
import { FormattedMessage } from 'react-intl';
import { useMapDataContext } from '../context/MapDataContext.jsx';

export default function Header({
    dataAvailable,
    dataFiles,
    handleNewUploadClick,
}) {

    const { data, mapDataDispatch } = useMapDataContext();
    const tags = data.features.reduce((accumulator, currentValue) => {
        if (currentValue.properties.tags) {
            Object.keys(currentValue.properties.tags).forEach(tagKey => {
                accumulator[tagKey] = (accumulator[tagKey] || 0) + 1;
            });
        }
        return accumulator;
    }, {});

    const selectTagHandler = tag => {
        mapDataDispatch({
            type: 'set_filter_tag',
            payload: {tag: tag},
        });
    }

    return (
        <>

        <header className="header">

            {/* Logo */}
            <h1 className={dataAvailable ? "titleSmall" : "title"} >
                <img src={logo} className="logo" alt="logo" />
                <span>ChatMap</span>
            </h1>

            {/* Options: upload new file, download */}
            { dataAvailable ?
            <>
                <div className="fileOptions">
                    <SaveButton data={data} dataFiles={dataFiles} />
                    <sl-button
                        variant="success"
                        outline
                        onClick={handleNewUploadClick}
                    >
                        <FormattedMessage
                            id = "app.uploadNewFile"
                            defaultMessage="Upload new file"
                        /> 
                    </sl-button>
                </div>
                <div className="tagsOptions">
                    <TagsOptions onSelectTag={selectTagHandler} tags={tags} selectedTag={data.filterTag} />
                </div>
            </>
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