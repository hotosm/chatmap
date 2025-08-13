import { useState, useEffect } from 'react';
import logo from '../assets/hot-logo.svg';
import SaveButton from '../components/SaveButton/index.jsx';
import TagsOptions from "../components/TagsOptions";
import { FormattedMessage } from 'react-intl';
import { useMapDataContext } from '../context/MapDataContext.jsx';
import NavBar from '../components/NavBar';

export default function Header({
    dataAvailable,
    dataFiles,
    handleNewUploadClick,
    handleOptionClick
}) {

    const { data, mapDataDispatch } = useMapDataContext();
    const tags = data.features.reduce((accumulator, currentValue) => {
        currentValue.properties?.tags?.forEach(tag => {
            accumulator[tag] = (accumulator[tag] || 0) + 1;
        });
        return accumulator;
    }, {});

    const selectTagHandler = tag => {
        mapDataDispatch({
            type: 'set_filter_tag',
            payload: {tag: tag},
        });
    }

    const [selected, setSelected] = useState(false);

    const onOptionClick = option => {
        setSelected(prev => !prev);
        handleOptionClick(option);
    }

    useEffect(() => {
        setSelected(false);
    }, [data])

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
                    <NavBar
                        onOptionClick={onOptionClick}
                        selected={selected}
                    >
                        <TagsOptions onSelectTag={selectTagHandler} tags={tags} selectedTag={data.filterTag} />
                    </NavBar>
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