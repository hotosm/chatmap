const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';

export function toBase64Url(bytes: Uint8Array): string {
    let result = '';

    for (let i = 0; i < bytes.length; i += 3) {
        const chunk = (bytes[i] << 16) | ((bytes[i + 1] ?? 0) << 8) | (bytes[i + 2] ?? 0);

        result += ALPHABET[(chunk >> 18) & 63] + ALPHABET[(chunk >> 12) & 63];

        if (i + 1 < bytes.length) {
            result += ALPHABET[(chunk >> 6) & 63];
        }

        if (i + 2 < bytes.length) {
            result += ALPHABET[chunk & 63];
        }
    }

    return result;
}
