import { useState, useEffect } from 'react';
import logo from '../assets/hot-logo.svg';
import SaveButton from '../components/SaveButton/index.jsx';
import TagsOptions from "../components/TagsOptions/index.jsx";
import { FormattedMessage } from 'react-intl';
import { useMapDataContext } from '../context/MapDataContext.jsx';
import NavBar from '../components/NavBar/index.jsx';

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
                    <span>ChatMap</span>
                </h1>
            </a>

            {/* Options: upload new file, download */}
            { dataAvailable ?
            <>
                <div className="fileOptions">
                    <SaveButton data={data} dataFiles={dataFiles} />
                    { showUploadButton ?
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
                    </sl-button> : null}
                </div>
                <div className="tagsOptions">
                    <NavBar
                        selected={selected}
                    >
                        { showChatIcon ?
                        <sl-button
                            size="small"
                            variant={`${selected && "success"}`}
                            onClick={ () => onOptionClick("chat") }
                        >
                            <sl-icon name="chat-square-dots"></sl-icon>
                        </sl-button>
                        : null }
                        <TagsOptions onSelectTag={selectTagHandler} tags={tags} selectedTag={data.filterTag} />
                    </NavBar>
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