export const createQueue = `
    CREATE TABLE queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        map_id TEXT NOT NULL REFERENCES maps (map_id) ON DELETE CASCADE,
        captured_at TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        message TEXT,
        media_uri TEXT,
        point_state TEXT NOT NULL DEFAULT 'unconfirmed'
            CHECK (point_state IN ('unconfirmed', 'created', 'rejected')),
        media_state TEXT
            CHECK (media_state IN ('waiting', 'uploaded', 'rejected')),
        point_id TEXT,
        rejection TEXT
    );
    CREATE INDEX queue_by_capture ON queue (captured_at, id);
    CREATE INDEX queue_by_map ON queue (map_id);
`;
