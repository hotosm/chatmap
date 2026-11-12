export type ConnectivityState = 'online' | 'offline';

export type MonitorParams = {
    intervalMs: number;
    failuresToOffline: number;
    retryMinMs: number;
    retryMaxMs: number;
};

type TimerHandle = ReturnType<typeof setTimeout>;

type Timers = {
    set: (callback: () => void, ms: number) => TimerHandle;
    clear: (handle: TimerHandle) => void;
};

export class ConnectivityMonitor {
    private readonly check: () => Promise<boolean>;
    private readonly params: MonitorParams;
    private readonly timers: Timers;
    private state: ConnectivityState = 'online';
    private failures = 0;
    private running = false;
    private timer: TimerHandle | null = null;
    private inFlight: Promise<void> | null = null;
    private readonly listeners = new Set<() => void>();
    private readonly reconnectListeners = new Set<() => void>();

    constructor(check: () => Promise<boolean>, params: MonitorParams, timers?: Timers) {
        this.check = check;
        this.params = params;
        this.timers = timers ?? {set: setTimeout, clear: clearTimeout};
    }

    getState = (): ConnectivityState => this.state;

    subscribe = (listener: () => void): (() => void) => {
        this.listeners.add(listener);

        return () => {
            this.listeners.delete(listener);
        };
    };

    onReconnect = (listener: () => void): (() => void) => {
        this.reconnectListeners.add(listener);

        return () => {
            this.reconnectListeners.delete(listener);
        };
    };

    start(): void {
        this.running = true;
        void this.checkNow();
    }

    stop(): void {
        this.running = false;
        this.clearTimer();
    }

    networkChanged(): void {
        void this.checkNow();
    }

    reportReachable(): void {
        this.failures = 0;
        this.setState('online');
        this.schedule();
    }

    reportUnreachable(): void {
        void this.checkNow();
    }

    checkNow(): Promise<void> {
        this.clearTimer();
        this.inFlight ??= this.runCheck().finally(() => {
            this.inFlight = null;
        });

        return this.inFlight;
    }

    private async runCheck(): Promise<void> {
        let reachable = false;

        try {
            reachable = await this.check();
        } catch {
            reachable = false;
        }

        if (reachable) {
            this.failures = 0;
            this.setState('online');
        } else {
            this.failures += 1;

            if (this.failures >= this.params.failuresToOffline) {
                this.setState('offline');
            }
        }

        this.schedule();
    }

    private schedule(): void {
        this.clearTimer();

        if (!this.running) {
            return;
        }

        this.timer = this.timers.set(() => {
            this.timer = null;
            void this.checkNow();
        }, this.nextDelay());
    }

    private nextDelay(): number {
        if (this.failures === 0) {
            return this.params.intervalMs;
        }

        return Math.min(this.params.retryMinMs * 2 ** (this.failures - 1), this.params.retryMaxMs);
    }

    private clearTimer(): void {
        if (this.timer !== null) {
            this.timers.clear(this.timer);
            this.timer = null;
        }
    }

    private setState(next: ConnectivityState): void {
        if (next === this.state) {
            return;
        }

        const previous = this.state;
        this.state = next;

        for (const listener of this.listeners) {
            listener();
        }

        if (previous === 'offline' && next === 'online') {
            for (const listener of this.reconnectListeners) {
                listener();
            }
        }
    }
}
