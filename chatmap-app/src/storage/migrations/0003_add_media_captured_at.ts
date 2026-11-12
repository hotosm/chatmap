// Media queued before this had no capture time of its own; the point's is the closest known
export const addMediaCapturedAt = `
    ALTER TABLE queue ADD COLUMN media_captured_at TEXT;
    UPDATE queue SET media_captured_at = captured_at WHERE media_uri IS NOT NULL;
`;
