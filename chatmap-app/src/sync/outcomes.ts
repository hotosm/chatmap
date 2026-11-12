export type PointOutcome =
    | {status: 'created'; pointId: string}
    | {status: 'rejected'; reason: string}
    | {status: 'retry'};

export type MediaOutcome =
    | {status: 'uploaded'}
    | {status: 'rejected'; reason: string}
    | {status: 'retry'};
