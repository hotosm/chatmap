import { useState } from "react";
import { useInterval } from "../../hooks/useInterval.js";

// The current time, updated every minute while on, so expired values show as unknown on their own
export default function useNow(on = true) {
    const [now, setNow] = useState(Date.now);
    useInterval(() => setNow(Date.now()), on ? 60 * 1000 : null);
    return now;
}
