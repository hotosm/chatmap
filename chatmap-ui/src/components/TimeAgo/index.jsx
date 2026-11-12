import { useIntl } from "react-intl";

const UNITS = [
    ["day", 24 * 60 * 60 * 1000],
    ["hour", 60 * 60 * 1000],
    ["minute", 60 * 1000],
];

// How long ago a date was, as { value, unit } for a relative time format
export const timeAgo = (datetime, now = Date.now()) => {
    const elapsed = now - new Date(datetime).getTime();
    if (isNaN(elapsed)) return null;
    for (const [unit, ms] of UNITS) {
        if (elapsed >= ms) return { value: -Math.floor(elapsed / ms), unit };
    }
    return { value: 0, unit: "minute" };
};

// "10 minutes ago", in the language of the page
export default function TimeAgo({ datetime }) {
    const intl = useIntl();
    const ago = timeAgo(datetime);

    if (!ago) return null;
    return intl.formatRelativeTime(ago.value, ago.unit, { numeric: "auto" });
}
