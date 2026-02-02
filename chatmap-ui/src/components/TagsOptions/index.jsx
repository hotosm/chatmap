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
                        />
                    </strong> :
                        <FormattedMessage
                            id = "app.all"
                            defaultMessage="All"
                        />
                    }
                </sl-menu-item>
                {Object.keys(tags).map(key =>
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
