import { FormattedMessage } from 'react-intl';

export default function TagsOptions({ tags, onSelectTag, selectedTag }) {
    return (
        <sl-dropdown>
            <sl-button size="small" slot="trigger" caret>
                { selectedTag ? selectedTag :
                    <FormattedMessage
                        id = "app.all"
                        defaultMessage="Tags"
                    />
                }
                <sl-icon slot="prefix" name="tags"></sl-icon>
            </sl-button>
            <sl-menu className="tagsMenu">
                <sl-menu-item key="all" onClick={() => onSelectTag(null)}>
                    {!selectedTag ?
                    <strong>
                        <FormattedMessage
                            id = "app.all"
                            defaultMessage="All"
                        /> ({tags["__all"]})
                    </strong>  :
                        <><FormattedMessage
                            id = "app.all"
                            defaultMessage="All"
                        /> ({tags["__all"]})</>
                    }
                </sl-menu-item>
                <sl-menu-item key="notag" onClick={() => onSelectTag(undefined)}>
                    {selectedTag === undefined ?
                    <strong>
                        <FormattedMessage
                            id = "app.notag"
                            defaultMessage="No tag"
                        /> ({tags["__undefined"]})
                    </strong> :
                        <><FormattedMessage
                            id = "app.notag"
                            defaultMessage="No tag"
                        /> ({tags["__undefined"]})</>
                    }
                </sl-menu-item>
                {Object.keys(tags).map(key =>
                    key !== "__all" && key !== "__undefined" &&
                    <sl-menu-item key={key} onClick={() => onSelectTag(key)}>
                        {selectedTag && selectedTag == key ?
                            <strong>{key} ({tags[key]})</strong>
                        : 
                            `${key} (${tags[key]})`
                        }
                    </sl-menu-item>
                )}
            </sl-menu>
        </sl-dropdown>
    );
}
