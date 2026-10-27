import {useEffect, useRef, useState} from 'react';
import {Modal, Pressable, StyleSheet, Text, View} from 'react-native';
import {Image} from 'expo-image';
import {CameraView, useMicrophonePermissions, type CameraMode} from 'expo-camera';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {deleteMedia} from '../../queue/media';
import {formatDuration} from '../duration';

const closeIcon = require('@/assets/icons/x-lg.svg');

function ElapsedTime({since}: {since: number}) {
    const [now, setNow] = useState(since);

    useEffect(() => {
        const timer = setInterval(() => setNow(Date.now()), 500);

        return () => clearInterval(timer);
    }, []);

    return (
        <View style={styles.cameraTimer}>
            <View style={styles.recordingDot} />
            <Text style={styles.cameraTimerText}>{formatDuration((now - since) / 1000)}</Text>
        </View>
    );
}

function ModeOption({label, selected, onPress}: {label: string; selected: boolean; onPress: () => void}) {
    return (
        <Pressable hitSlop={8} onPress={onPress}>
            <Text style={[styles.cameraMode, selected && styles.cameraModeSelected]}>{label}</Text>
        </Pressable>
    );
}

function shutterStyle(mode: CameraMode, recording: boolean) {
    if (mode === 'picture') {
        return styles.shutterInner;
    }

    return recording ? styles.shutterStop : styles.shutterRecord;
}

export function CameraModal({onClose, onCapture}: {
    onClose: () => void;
    onCapture: (uri: string) => void;
}) {
    const insets = useSafeAreaInsets();
    const cameraRef = useRef<CameraView>(null);
    const discardRecording = useRef(false);
    const [cameraReady, setCameraReady] = useState(false);
    const [mode, setMode] = useState<CameraMode>('picture');
    const [recordingSince, setRecordingSince] = useState<number | null>(null);
    const [, requestMicrophonePermission] = useMicrophonePermissions();
    const recording = recordingSince !== null;

    const selectMode = async (next: CameraMode) => {
        if (next === 'video') {
            const {granted} = await requestMicrophonePermission();
            if (!granted) {
                console.error('Microphone permission denied');
                return;
            }
        }

        setMode(next);
    };

    const takePicture = async () => {
        try {
            const picture = await cameraRef.current?.takePictureAsync();
            if (picture) {
                onCapture(picture.uri);
            }
        } catch (error) {
            console.error('Error getting the picture', error);
        }
    };

    const recordVideo = async () => {
        setRecordingSince(Date.now());

        try {
            const video = await cameraRef.current?.recordAsync();

            if (video && discardRecording.current) {
                deleteMedia(video.uri);
            } else if (video) {
                onCapture(video.uri);
            }
        } catch (error) {
            console.error('Error recording the video', error);
        } finally {
            setRecordingSince(null);
        }
    };

    const pressShutter = () => {
        if (mode === 'picture') {
            void takePicture();
        } else if (recording) {
            cameraRef.current?.stopRecording();
        } else {
            void recordVideo();
        }
    };

    const close = () => {
        if (recording) {
            discardRecording.current = true;
            cameraRef.current?.stopRecording();
        }

        onClose();
    };

    return (
        <Modal animationType="slide" onRequestClose={close}>
            <View style={styles.camera}>
                <CameraView
                    ref={cameraRef}
                    style={StyleSheet.absoluteFill}
                    facing="back"
                    mode={mode}
                    onCameraReady={() => setCameraReady(true)}
                />
                <Pressable onPress={close} style={[styles.cameraClose, {top: insets.top + 12}]}>
                    <Image source={closeIcon} tintColor="#fff" style={styles.cameraCloseIcon} />
                </Pressable>
                {recordingSince !== null && (
                    <View style={[styles.cameraStatus, {top: insets.top + 16}]}>
                        <ElapsedTime since={recordingSince} />
                    </View>
                )}
                <View style={[styles.cameraControls, {paddingBottom: insets.bottom + 24}]}>
                    {!recording && (
                        <View style={styles.cameraModes}>
                            <ModeOption
                                label="Photo"
                                selected={mode === 'picture'}
                                onPress={() => void selectMode('picture')}
                            />
                            <ModeOption
                                label="Video"
                                selected={mode === 'video'}
                                onPress={() => void selectMode('video')}
                            />
                        </View>
                    )}
                    <Pressable
                        onPress={pressShutter}
                        disabled={!cameraReady}
                        style={[styles.shutter, !cameraReady && styles.disabled]}
                    >
                        <View style={shutterStyle(mode, recording)} />
                    </Pressable>
                </View>
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    camera: {
        flex: 1,
        backgroundColor: '#000',
    },
    cameraClose: {
        position: 'absolute',
        left: 12,
        padding: 8,
    },
    cameraCloseIcon: {
        width: 24,
        height: 24,
    },
    cameraStatus: {
        position: 'absolute',
        left: 0,
        right: 0,
        alignItems: 'center',
    },
    cameraTimer: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        paddingHorizontal: 12,
        paddingVertical: 4,
        borderRadius: 12,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
    },
    cameraTimerText: {
        color: '#fff',
        fontSize: 16,
        fontVariant: ['tabular-nums'],
    },
    recordingDot: {
        width: 10,
        height: 10,
        borderRadius: 5,
        backgroundColor: '#F34D47',
    },
    cameraControls: {
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: 0,
        alignItems: 'center',
    },
    cameraModes: {
        flexDirection: 'row',
        gap: 24,
        marginBottom: 16,
    },
    cameraMode: {
        color: 'rgba(255, 255, 255, 0.7)',
        fontSize: 14,
        fontWeight: '600',
        letterSpacing: 1,
        textTransform: 'uppercase',
    },
    cameraModeSelected: {
        color: '#FFD60A',
    },
    shutter: {
        width: 72,
        height: 72,
        borderRadius: 36,
        borderWidth: 4,
        borderColor: '#fff',
        alignItems: 'center',
        justifyContent: 'center',
    },
    shutterInner: {
        width: 56,
        height: 56,
        borderRadius: 28,
        backgroundColor: '#fff',
    },
    shutterRecord: {
        width: 56,
        height: 56,
        borderRadius: 28,
        backgroundColor: '#F34D47',
    },
    shutterStop: {
        width: 28,
        height: 28,
        borderRadius: 4,
        backgroundColor: '#F34D47',
    },
    disabled: {
        opacity: 0.5,
    },
});
