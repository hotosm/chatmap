import React, { useState } from "react";

function NavBar({ onOptionClick, children }) {

    const [selected, setSelected] = useState(false);

    const handleOptionClick = option => {
        if (option === "chat") {
            setSelected(prev => !prev);
            onOptionClick(option);
        }
    }

    return (
    <>
        <div className="appNav">
            <sl-button
                size="small"
                variant={`${selected && "success"}`}
                onClick={ () => handleOptionClick("chat") }
            >
                <sl-icon name="chat-square-dots"></sl-icon>
            </sl-button>
            <span>
                {children}
            </span>
        </div>
    </>
    );
}

export default NavBar;
