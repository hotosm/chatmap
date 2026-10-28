import {useEffect, useRef, useState} from 'react';
import {Alert, Pressable, ScrollView, StyleSheet, Text, View} from 'react-native';
import {router, Stack, useLocalSearchParams} from 'expo-router';
import {useCameraPermissions} from 'expo-camera';
import {RecordingPresets, requestRecordingPermissionsAsync, useAudioRecorder} from 'expo-audio';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {Button} from '../../components/Button';
import {CameraModal} from '../../components/map/CameraModal';
import {MessageInputBar, RecordingBar} from '../../components/map/InputBar';
import {LocationPicker} from '../../components/map/LocationPicker';
import {MapHeader} from '../../components/map/MapHeader';
import {PointEntry} from '../../components/map/PointEntry';
import {setRecordingMode} from '../../components/map/recordingMode';
import {useEntries} from '../../hooks/useEntries';
import {onMapsRemoved} from '../../contributor/refreshMaps';
import {useMapLookup} from '../../hooks/useMapLookup';
import {addMedia, capturePoint, dismissItem, leaveMap} from '../../queue/service';

function goHome() {
    if (router.canGoBack()) {
        router.back();
    } else {
        router.replace('/');
    }
}

function Notice({text, onPress}: {text: string; onPress?: () => void}) {
    return (
        <Pressable disabled={!onPress} onPress={onPress} style={styles.notice}>
            <Text style={styles.noticeText}>{text}</Text>
        </Pressable>
    );
}

export default function MapperScreen() {
    const {id} = useLocalSearchParams<{id: string}>();
    const insets = useSafeAreaInsets();
    const scrollRef = useRef<ScrollView>(null);
    const stickToBottom = useRef(true);
    const [awaitingMedia, setAwaitingMedia] = useState<number | null>(null);
    const [cameraOpen, setCameraOpen] = useState(false);
    const [pickerOpen, setPickerOpen] = useState(false);
    const [recordingAudio, setRecordingAudio] = useState(false);
    const [, requestCameraPermission] = useCameraPermissions();
    const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
    const map = useMapLookup(id);
    const {entries, hasOlder, status, loadingOlder, loadOlder, reload, online} = useEntries(id);

    useEffect(() => () => leaveMap(id), [id]);

    useEffect(
        () => onMapsRemoved((removed) => {
            if (removed.some((removal) => removal.map.mapId === id)) {
                goHome();
            }
        }),
        [id],
    );

    useEffect(() => {
        setRecordingMode(false).catch((error) => console.warn('Setting the audio mode failed', error));
    }, []);

    const sendLocation = async (latitude: number, longitude: number) => {
        setPickerOpen(false);

        try {
            stickToBottom.current = true;
            setAwaitingMedia(await capturePoint(id, latitude, longitude));
        } catch (error) {
            console.error('Failed to save the location:', error);
        }
    };

    const openCamera = async () => {
        const {granted} = await requestCameraPermission();
        if (!granted) {
            console.error('Camera permission denied');
            return;
        }

        setCameraOpen(true);
    };

    const startAudio = async () => {
        try {
            const {granted} = await requestRecordingPermissionsAsync();
            if (!granted) {
                console.error('Microphone permission denied');
                return;
            }

            await setRecordingMode(true);
            await recorder.prepareToRecordAsync();
            recorder.record();
            setRecordingAudio(true);
        } catch (error) {
            console.error('Failed to start the recording:', error);
        }
    };

    const saveMedia = async (uri: string) => {
        setCameraOpen(false);

        if (awaitingMedia === null) {
            return;
        }

        try {
            stickToBottom.current = true;

            if (!(await addMedia(awaitingMedia, uri))) {
                Alert.alert('Media not attached', 'The point was not accepted, so the media was discarded.');
            }
        } catch (error) {
            console.error('Failed to save the media:', error);
            Alert.alert('Media not saved', 'The media could not be saved on this device.');
        } finally {
            setAwaitingMedia(null);
        }
    };

    const finishAudio = (uri: string | null) => {
        setRecordingAudio(false);

        if (uri) {
            void saveMedia(uri);
        }
    };

    const showOlder = () => {
        stickToBottom.current = false;
        void loadOlder();
    };

    if (map.status === 'missing') {
        return (
            <View style={styles.missing}>
                <Stack.Screen options={{title: 'Map'}} />
                <Text style={styles.noticeText}>This map is not in your list anymore.</Text>
                <Button label="Back to my maps" onPress={() => router.replace('/')} />
            </View>
        );
    }

    return (
        <View style={styles.mapper}>
            <Stack.Screen options={{headerShown: false}} />
            <ScrollView
                ref={scrollRef}
                contentContainerStyle={[styles.messages, {paddingTop: insets.top + 70}]}
                onContentSizeChange={() => {
                    if (stickToBottom.current) {
                        scrollRef.current?.scrollToEnd();
                    }
                }}
            >
                {hasOlder && (
                    <Notice text={loadingOlder ? 'Loading…' : 'Load older points'} onPress={showOlder} />
                )}
                {!online && entries.length === 0 && <Notice text="History is not available offline." />}
                {status === 'error' && <Notice text="Could not load your history. Tap to retry." onPress={() => void reload()} />}
                {status === 'forbidden' && <Notice text="You no longer have access to this map." />}
                {entries.map((entry) => (
                    <PointEntry key={entry.key} entry={entry} onDismiss={(queueId) => void dismissItem(queueId)} />
                ))}
            </ScrollView>
            <MapHeader onLogoPress={goHome} />
            {recordingAudio ? (
                <RecordingBar recorder={recorder} onFinish={finishAudio} />
            ) : (
                <MessageInputBar
                    locationShared={awaitingMedia !== null}
                    onLocationPress={() => setPickerOpen(true)}
                    onCameraPress={openCamera}
                    onMicrophonePress={startAudio}
                />
            )}
            {cameraOpen && <CameraModal onClose={() => setCameraOpen(false)} onCapture={saveMedia} />}
            {pickerOpen && (
                <LocationPicker
                    online={online}
                    onClose={() => setPickerOpen(false)}
                    onPick={(latitude, longitude) => void sendLocation(latitude, longitude)}
                />
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    mapper: {
        flex: 1,
        backgroundColor: '#F7F8F9',
    },
    messages: {
        paddingHorizontal: 20,
        paddingBottom: 10,
        gap: 10,
    },
    notice: {
        paddingVertical: 8,
    },
    noticeText: {
        color: '#71829E',
        fontSize: 14,
    },
    missing: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        gap: 16,
        padding: 24,
        backgroundColor: '#F7F8F9',
    },
});
