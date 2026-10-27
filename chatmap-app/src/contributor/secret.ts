import * as Crypto from 'expo-crypto';
import * as SecureStore from 'expo-secure-store';

import {toBase64Url} from './base64url';

const SECRET_KEY = 'contributor-secret';
const SECRET_BYTES = 32;

let pending: Promise<string> | null = null;

async function loadOrCreate(): Promise<string> {
    const stored = await SecureStore.getItemAsync(SECRET_KEY);

    if (stored) {
        return stored;
    }

    const secret = toBase64Url(await Crypto.getRandomBytesAsync(SECRET_BYTES));
    await SecureStore.setItemAsync(SECRET_KEY, secret);

    return secret;
}

export function getSecret(): Promise<string> {
    pending ??= loadOrCreate().catch((error) => {
        pending = null;
        throw error;
    });

    return pending;
}
