import type {SQLiteDatabase} from 'expo-sqlite';

import {MIGRATIONS} from './migrations';

export type Database = Pick<
    SQLiteDatabase,
    'execAsync' | 'runAsync' | 'getAllAsync' | 'getFirstAsync' | 'withExclusiveTransactionAsync'
>;

export async function migrate(db: Database): Promise<void> {
    const row = await db.getFirstAsync<{user_version: number}>('PRAGMA user_version');
    const current = row?.user_version ?? 0;

    for (let version = current; version < MIGRATIONS.length; version++) {
        await db.withExclusiveTransactionAsync(async (txn) => {
            await txn.execAsync(MIGRATIONS[version]);
            await txn.execAsync(`PRAGMA user_version = ${version + 1}`);
        });
    }
}
