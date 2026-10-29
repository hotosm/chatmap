export const createMaps = `
    CREATE TABLE maps (
        map_id TEXT PRIMARY KEY NOT NULL,
        map_name TEXT,
        nickname TEXT NOT NULL,
        position INTEGER NOT NULL
    );
    CREATE TABLE meta (
        key TEXT PRIMARY KEY NOT NULL,
        value TEXT NOT NULL
    );
`;
