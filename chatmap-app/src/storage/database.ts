import * as SQLite from 'expo-sqlite';

import {migrate} from './schema';

const DATABASE_NAME = 'chatmap.db';

let pending: Promise<SQLite.SQLiteDatabase> | null = null;

async function open(): Promise<SQLite.SQLiteDatabase> {
    const db = await SQLite.openDatabaseAsync(DATABASE_NAME);

    await db.execAsync('PRAGMA journal_mode = WAL');
    await db.execAsync('PRAGMA foreign_keys = ON');
    await migrate(db);

    return db;
}

export function getDatabase(): Promise<SQLite.SQLiteDatabase> {
    pending ??= open().catch((error) => {
        pending = null;
        throw error;
    });

    return pending;
}
