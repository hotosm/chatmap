import type {QueueItem} from '../queue/store';
import type {MediaOutcome, PointOutcome} from './outcomes';

export type UploadableItem = QueueItem & {pointId: string; mediaUri: string; mediaCapturedAt: string};

export type EngineDeps = {
    isOnline: () => boolean;
    next: () => Promise<QueueItem | null>;
    markCreated: (id: number, pointId: string) => Promise<void>;
    markPointRejected: (id: number, reason: string) => Promise<void>;
    markMediaUploaded: (id: number) => Promise<void>;
    markMediaRejected: (id: number, reason: string) => Promise<void>;
    cleanup: () => Promise<void>;
    createPoint: (item: QueueItem) => Promise<PointOutcome>;
    uploadMedia: (item: UploadableItem) => Promise<MediaOutcome>;
    onChange: () => void;
    log: (message: string, error: unknown) => void;
};

export type RetryParams = {
    retryMinMs: number;
    retryMaxMs: number;
};

type TimerHandle = ReturnType<typeof setTimeout>;

type Timers = {
    set: (callback: () => void, ms: number) => TimerHandle;
    clear: (handle: TimerHandle) => void;
};

export class SyncEngine {
    private readonly deps: EngineDeps;
    private readonly params: RetryParams;
    private readonly timers: Timers;
    private running = false;
    private again = false;
    private failures = 0;
    private timer: TimerHandle | null = null;

    constructor(deps: EngineDeps, params: RetryParams, timers?: Timers) {
        this.deps = deps;
        this.params = params;
        this.timers = timers ?? {set: setTimeout, clear: clearTimeout};
    }

    request(): void {
        if (this.running) {
            this.again = true;
            return;
        }

        void this.run();
    }

    restart(): void {
        this.failures = 0;
        this.request();
    }

    private async run(): Promise<void> {
        this.running = true;

        try {
            do {
                this.again = false;
                await this.pass();
            } while (this.again);
        } finally {
            this.running = false;
        }

        try {
            await this.deps.cleanup();
            this.deps.onChange();
        } catch (error) {
            this.deps.log('Cleaning up the queue failed', error);
        }
    }

    private async pass(): Promise<void> {
        this.clearTimer();

        if (!this.deps.isOnline()) {
            return;
        }

        let stalled = false;

        try {
            while (await this.processNext()) {
                this.deps.onChange();
            }
        } catch (error) {
            this.deps.log('Sending the queue failed', error);
            stalled = true;
        }

        if (stalled) {
            this.scheduleRetry();
        } else {
            this.failures = 0;
        }
    }

    private async processNext(): Promise<boolean> {
        const item = await this.deps.next();

        if (!item) {
            return false;
        }

        if (item.pointState === 'unconfirmed') {
            return this.sendPoint(item);
        }

        return this.sendMedia(item);
    }

    private async sendPoint(item: QueueItem): Promise<boolean> {
        const outcome = await this.deps.createPoint(item);

        if (outcome.status === 'created') {
            await this.deps.markCreated(item.id, outcome.pointId);
            return true;
        }

        if (outcome.status === 'rejected') {
            await this.deps.markPointRejected(item.id, outcome.reason);
            return true;
        }

        throw new Error('The server could not take the point right now');
    }

    private async sendMedia(item: QueueItem): Promise<boolean> {
        if (item.pointId === null || item.mediaUri === null || item.mediaCapturedAt === null) {
            await this.deps.markMediaRejected(item.id, 'invalid');
            return true;
        }

        const outcome = await this.deps.uploadMedia({
            ...item,
            pointId: item.pointId,
            mediaUri: item.mediaUri,
            mediaCapturedAt: item.mediaCapturedAt,
        });

        if (outcome.status === 'uploaded') {
            await this.deps.markMediaUploaded(item.id);
            return true;
        }

        if (outcome.status === 'rejected') {
            await this.deps.markMediaRejected(item.id, outcome.reason);
            return true;
        }

        throw new Error('The server could not take the media right now');
    }

    private scheduleRetry(): void {
        this.failures += 1;

        const delay = Math.min(this.params.retryMinMs * 2 ** (this.failures - 1), this.params.retryMaxMs);

        this.timer = this.timers.set(() => {
            this.timer = null;
            this.request();
        }, delay);
    }

    private clearTimer(): void {
        if (this.timer !== null) {
            this.timers.clear(this.timer);
            this.timer = null;
        }
    }
}
