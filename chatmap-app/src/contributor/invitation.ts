const INVITATION_PATTERN = /^hot-chatmap:\/\/join\?token=([A-Za-z0-9_-]+)$/;

export function parseInvitation(data: string): string | null {
    return INVITATION_PATTERN.exec(data.trim())?.[1] ?? null;
}
