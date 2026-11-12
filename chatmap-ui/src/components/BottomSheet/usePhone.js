import { useEffect, useState } from "react";

// Below this width the panels of the dashboard go in a BottomSheet (the breakpoint of messages.css)
export const PHONE = "(max-width: 720px)";

/**
 * Whether the screen is as narrow as a phone's, following it as it changes.
 * Without matchMedia (tests), it is not.
 */
export default function usePhone() {
    const query = typeof window !== "undefined" && window.matchMedia ? window.matchMedia(PHONE) : null;
    const [phone, setPhone] = useState(Boolean(query && query.matches));

    useEffect(() => {
        if (!query) return;
        const change = (event) => setPhone(event.matches);
        query.addEventListener("change", change);
        setPhone(query.matches);
        return () => query.removeEventListener("change", change);
    }, []);

    return phone;
}
