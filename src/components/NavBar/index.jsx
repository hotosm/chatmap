import React from "react";
import { FormattedMessage } from 'react-intl';

function NavBar({ onOptionClick }) {

    return (
    <>
        <div className="appNav">
            <button className="textButton" onClick={ () => onOptionClick("options") }>
            <FormattedMessage
                id = "app.options"
                defaultMessage="Options"
            />
            </button>
        </div>
    </>
    );
}

export default NavBar;
