import React from "react";
import { FormattedMessage } from 'react-intl';

function NavBar({ onOptionClick }) {

    return (
    <>
        <div className="appNav">
            <sl-button
                variant="text"
                onClick={ () => onOptionClick("options") }
            >
            <FormattedMessage
                id = "app.options"
                defaultMessage="Options"
            />
            </sl-button>
        </div>
    </>
    );
}

export default NavBar;
