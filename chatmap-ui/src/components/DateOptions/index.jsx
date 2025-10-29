export default function DateOptions({ onSelectDate, selectedDate }) {

    const dateOptions = [
        ["All", 0],
        ["Last hour", 1],
        ["3 hs", 3],
        ["6 hs", 6],
        ["12 hs", 12],
        ["1 day", 24],
    ];

    return (
        <sl-dropdown>
            <sl-button size="small" slot="trigger" caret>
                { selectedDate ? `${selectedDate} hs` : null }
                <sl-icon slot="prefix" name="calendar-range"></sl-icon>
            </sl-button>
            <sl-menu>
                { dateOptions.map( dateOption => (
                    <sl-menu-item key={dateOption[1]} onClick={() => onSelectDate(dateOption[1])}>
                        {dateOption[0]}
                    </sl-menu-item>
                ))}
            </sl-menu>
        </sl-dropdown>
    );
}
