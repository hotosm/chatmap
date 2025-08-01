function NavBar({ children }) {
    return (
    <>
        <div className="appNav">
            <span>
                {children}
            </span>
        </div>
    </>
    );
}

export default NavBar;
