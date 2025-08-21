import { useState, useEffect } from 'react';
import logo from '../assets/hot-logo.svg';
import SaveButton from '../components/SaveButton/index.jsx';
import TagsOptions from "../components/TagsOptions/index.jsx";
import { FormattedMessage } from 'react-intl';
import { useMapDataContext } from '../context/MapDataContext.jsx';

export default function Header({
    dataAvailable,
    dataFiles,
    handleNewUploadClick,
    handleOptionClick,
    showUploadButton,
    showChatIcon,
    legend,
    subtitle
}) {

    const { data, mapDataDispatch } = useMapDataContext();
    const tags = data.features.reduce((accumulator, currentValue) => {
        if (currentValue.properties.tags) {
            currentValue.properties.tags.forEach(tag => {
                accumulator[tag] = (accumulator[tag] || 0) + 1;
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

        <header className={`header ${dataAvailable && "headerSmall"}`}>

            {/* Logo */}
            <a href="/" className="logoLink">
                <h1 className={dataAvailable ? "titleSmall" : "title"} >
                    <img src={logo} className="logo" alt="logo" />
                    <span><strong>ChatMap</strong></span>
                </h1>
            </a>

            {/* Options: upload new file, download */}
            { dataAvailable ?
            <>
                <div className="mapOptions">
                    <SaveButton data={data} dataFiles={dataFiles} />
                    { showUploadButton ?
                    <div className="newFile">
                        <sl-button
                            variant="success"
                            outline
                            size="small"
                            onClick={handleNewUploadClick}
                        >
                            <sl-icon name="arrow-clockwise" slot="prefix"></sl-icon>
                            <FormattedMessage
                                id = "app.uploadNewFile"
                                defaultMessage="New file"
                            /> 
                        </sl-button>
                    </div> : null}
                    <div className="tagsOptions">
                        <TagsOptions
                            onSelectTag={selectTagHandler}
                            tags={tags}
                            selectedTag={data.filterTag}
                        />
                    </div>
                    { showChatIcon ?
                    <div className="chatIcon">
                        <sl-icon-button
                            name="chat-square-dots"
                            size="small"
                            onClick={ () => onOptionClick("chat") }
                        >
                        </sl-icon-button>
                    </div> : null}
                </div>
            </>
            :
            <>
            {/* Main legend */}
            <h2 className="subtitle">
                {subtitle ? subtitle :
                <FormattedMessage
                id = "app.subtitle"
                defaultMessage="Export and upload a chat to create a map"
                />}
            </h2>
            <p className="highlighted">
                { legend ? legend :
                <FormattedMessage
                id = "app.supportedApps"
                defaultMessage="Now it works with WhatsApp, Telegram or Signal!"
                />}
            </p>
            </>
            }
        </header>
    </>
    );
}