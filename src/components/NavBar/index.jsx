function NavBar({ onOptionClick, children, selected }) {

    const handleOptionClick = option => {
        onOptionClick(option);
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
