import {useEffect, useState} from 'react';
import {useAudioPlayer, useAudioPlayerStatus} from 'expo-audio';
import {Image} from 'expo-image';
import {useVideoPlayer, VideoView} from 'expo-video';
import {Pressable, StyleSheet, Text, View} from 'react-native';

import type {MediaKind} from '../../queue/media';
import type {MediaState, PointState} from '../../queue/store';
import {formatDuration} from '../duration';

export type EntrySource = {
    uri: string;
    headers?: Record<string, string>;
};

export type EntryMedia = {
    kind: MediaKind;
    source: EntrySource;
    time: number | null;
    state: MediaState;
};

export type Entry = {
    key: string;
    time: number;
    latitude: number;
    longitude: number;
    point: PointState;
    media: EntryMedia | null;
    rejection: string | null;
    queueId: number | null;
};

const tileHeaders = process.env.EXPO_OS === 'web' ? undefined : {'User-Agent': 'chatmap-app/1.0.0'};

const icons = {
    play: require('@/assets/icons/play-fill.svg'),
    pause: require('@/assets/icons/pause-fill.svg'),
};

const CAPTURE_TIME_FORMAT: Intl.DateTimeFormatOptions = {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
};

const getTileURL = (lon: number, lat: number) => {
    const zoom = 18;
    const latTile = Math.floor((1 - Math.log(Math.tan(lat * Math.PI / 180) + 1 / Math.cos(lat * Math.PI / 180)) / Math.PI) / 2 * Math.pow(2, zoom));
    const lonTile = Math.floor((lon + 180) / 360 * Math.pow(2, zoom));
    return `https://tile.openstreetmap.org/${zoom}/${lonTile}/${latTile}.png`;
};

const POINT_REASONS: Record<string, string> = {
    '403': 'You can no longer contribute to this map.',
    '404': 'This map no longer exists.',
    '422': 'The server rejected this point.',
};

const MEDIA_REASONS: Record<string, (kind: MediaKind) => string> = {
    '403': (kind) => `This ${kind} could not be attached to its point.`,
    '415': () => 'This file type is not supported.',
    '422': (kind) => `The server rejected this ${kind}.`,
    'missing-file': (kind) => `The ${kind} is no longer on this device.`,
    invalid: (kind) => `This ${kind} could not be sent.`,
};

function CaptureTime({time}: {time: number}) {
    return <Text style={styles.time}>{new Date(time).toLocaleString(undefined, CAPTURE_TIME_FORMAT)}</Text>;
}

function Mark({symbol, color, label}: {symbol: string; color: string; label: string}) {
    return <Text accessibilityLabel={label} style={[styles.mark, {color}]}>{symbol}</Text>;
}

function PointMark({state}: {state: PointState}) {
    switch (state) {
        case 'unconfirmed':
            return <Mark symbol="⏳" color="#71829E" label="Sending"/>;
        case 'created':
            return <Mark symbol="✓" color="#2E7D32" label="Sent"/>;
        case 'rejected':
            return <Mark symbol="✗" color="#B00020" label="Rejected"/>;
    }
}

function MediaMark({state}: {state: MediaState}) {
    switch (state) {
        case 'waiting':
            return <Mark symbol="⏳" color="#71829E" label="Media sending"/>;
        case 'uploaded':
            return <Mark symbol="✓" color="#2E7D32" label="Media sent"/>;
        case 'rejected':
            return <Mark symbol="✗" color="#B00020" label="Media rejected"/>;
    }
}

function LocationMessage({entry}: {entry: Entry}) {
    return (
        <View style={styles.message}>
            <Image
                source={{uri: getTileURL(entry.longitude, entry.latitude), headers: tileHeaders}}
                style={styles.messageImage}
            />
            <View style={styles.locationPin}>
                <View style={styles.locationPinHead}/>
                <View style={styles.locationPinStem}/>
            </View>
            <View style={styles.markRow}>
                <CaptureTime time={entry.time}/>
                <PointMark state={entry.point}/>
            </View>
        </View>
    );
}

function VideoPlayback({source}: {source: EntrySource}) {
    const player = useVideoPlayer(source, (player) => player.play());

    return <VideoView player={player} nativeControls contentFit="contain" style={[styles.messageImage, styles.video]}/>;
}

function VideoContent({source}: {source: EntrySource}) {
    const [started, setStarted] = useState(false);

    if (started) {
        return <VideoPlayback source={source}/>;
    }

    return (
        <Pressable
            accessibilityLabel="Play video"
            onPress={() => setStarted(true)}
            style={[styles.messageImage, styles.video]}
        >
            <Image source={icons.play} tintColor="#fff" style={styles.videoPlay}/>
        </Pressable>
    );
}

function AudioControls({playing, progress, label, onPress}: {
    playing: boolean;
    progress: number;
    label: string;
    onPress: () => void;
}) {
    return (
        <View style={styles.audio}>
            <Pressable accessibilityLabel={playing ? 'Pause audio' : 'Play audio'} hitSlop={8} onPress={onPress}>
                <Image source={playing ? icons.pause : icons.play} tintColor="#2C3038" style={styles.audioButton}/>
            </Pressable>
            <View style={styles.audioTrack}>
                <View style={[styles.audioProgress, {width: `${Math.min(progress, 1) * 100}%`}]}/>
            </View>
            <Text style={styles.audioTime}>{label}</Text>
        </View>
    );
}

function AudioPlayback({source}: {source: EntrySource}) {
    const player = useAudioPlayer(source);
    const status = useAudioPlayerStatus(player);

    useEffect(() => {
        player.play();
    }, [player]);

    useEffect(() => {
        if (status.didJustFinish) {
            player.pause();
            void player.seekTo(0);
        }
    }, [player, status.didJustFinish]);

    const progress = status.duration > 0 ? status.currentTime / status.duration : 0;
    const shown = status.playing || status.currentTime > 0 ? status.currentTime : status.duration;

    return (
        <AudioControls
            playing={status.playing}
            progress={progress}
            label={formatDuration(shown)}
            onPress={() => (status.playing ? player.pause() : player.play())}
        />
    );
}

function AudioContent({source}: {source: EntrySource}) {
    const [started, setStarted] = useState(false);

    if (started) {
        return <AudioPlayback source={source}/>;
    }

    return <AudioControls playing={false} progress={0} label="Audio" onPress={() => setStarted(true)}/>;
}

function MediaMessage({media, pointRejected}: {media: EntryMedia; pointRejected: boolean}) {
    return (
        <View style={styles.message}>
            {media.kind === 'photo' && <Image source={media.source} style={styles.messageImage}/>}
            {/* Keyed by source: when it switches from the local file to the server, the player starts over idle */}
            {media.kind === 'video' && <VideoContent key={media.source.uri} source={media.source}/>}
            {media.kind === 'audio' && <AudioContent key={media.source.uri} source={media.source}/>}
            {(media.time !== null || !pointRejected) && (
                <View style={styles.markRow}>
                    {media.time !== null && <CaptureTime time={media.time}/>}
                    {!pointRejected && <MediaMark state={media.state}/>}
                </View>
            )}
        </View>
    );
}

function rejectionText(entry: Entry): string | null {
    if (entry.point === 'rejected') {
        return POINT_REASONS[entry.rejection ?? ''] ?? 'This point was rejected.';
    }

    if (entry.media?.state === 'rejected') {
        const reason = MEDIA_REASONS[entry.rejection ?? ''];

        return reason ? reason(entry.media.kind) : `This ${entry.media.kind} was rejected.`;
    }

    return null;
}

export function PointEntry({entry, onDismiss}: {entry: Entry; onDismiss: (queueId: number) => void}) {
    const reason = rejectionText(entry);

    return (
        <View style={styles.entry}>
            <LocationMessage entry={entry}/>
            {entry.media && <MediaMessage media={entry.media} pointRejected={entry.point === 'rejected'}/>}
            {reason && (
                <View style={styles.rejection}>
                    <Text style={styles.rejectionText}>{reason}</Text>
                    {entry.queueId !== null && (
                        <Pressable onPress={() => onDismiss(entry.queueId as number)}>
                            <Text style={styles.dismiss}>Dismiss</Text>
                        </Pressable>
                    )}
                </View>
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    entry: {
        gap: 10,
    },
    message: {
        width: 204,
        paddingTop: 4,
        paddingRight: 4,
        backgroundColor: '#fff',
        borderRadius: 3,
        boxShadow: '1px 1px 0px rgba(0, 0, 0, 0.05)',
    },
    messageImage: {
        width: '100%',
        aspectRatio: 1,
        borderRadius: 3,
    },
    video: {
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#2C3038',
    },
    videoPlay: {
        width: 48,
        height: 48,
    },
    audio: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
        paddingTop: 6,
        paddingLeft: 8,
    },
    audioButton: {
        width: 24,
        height: 24,
    },
    audioTrack: {
        flex: 1,
        height: 3,
        borderRadius: 2,
        backgroundColor: '#BFC8D6',
        overflow: 'hidden',
    },
    audioProgress: {
        height: '100%',
        backgroundColor: '#344F7B',
    },
    audioTime: {
        minWidth: 32,
        color: '#71829E',
        fontSize: 12,
        textAlign: 'right',
    },
    locationPin: {
        position: 'absolute',
        top: 84,
        left: 88,
    },
    locationPinHead: {
        width: 20,
        height: 20,
        borderRadius: 10,
        backgroundColor: '#F34D47',
        boxShadow: '1px 1px 0px rgba(0, 0, 0, 0.1)',
    },
    locationPinStem: {
        width: 2,
        height: 10,
        marginLeft: 9,
        backgroundColor: '#F34D47',
        boxShadow: '1px 1px 0px rgba(0, 0, 0, 0.1)',
    },
    markRow: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'flex-end',
        gap: 6,
        paddingVertical: 2,
    },
    time: {
        color: '#71829E',
        fontSize: 12,
    },
    mark: {
        fontSize: 13,
        fontWeight: '600',
    },
    rejection: {
        width: 204,
        gap: 4,
    },
    rejectionText: {
        color: '#B00020',
        fontSize: 13,
    },
    dismiss: {
        color: '#2C3038',
        fontSize: 13,
        fontWeight: '600',
    },
});
