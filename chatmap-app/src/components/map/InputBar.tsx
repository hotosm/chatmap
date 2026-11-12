import {useState} from 'react';
import {StyleSheet, Text, TextInput, View} from 'react-native';
import {useAudioRecorderState, type AudioRecorder} from 'expo-audio';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {deleteMedia} from '../../queue/media';
import {formatDuration} from '../duration';
import {IconButton} from './IconButton';
import {setRecordingMode} from './recordingMode';

const icons = {
    chatHeart: require('@/assets/icons/chat-heart.svg'),
    camera: require('@/assets/icons/camera.svg'),
    microphone: require('@/assets/icons/mic.svg'),
    stop: require('@/assets/icons/stop-fill.svg'),
    trash: require('@/assets/icons/trash.svg'),
};

export function MessageInputBar({locationShared, onLocationPress, onCameraPress, onMicrophonePress}: {
    locationShared: boolean;
    onLocationPress: () => void;
    onCameraPress: () => void;
    onMicrophonePress: () => void;
}) {
    const insets = useSafeAreaInsets();

    return (
        <View style={[styles.messageInputWrapper, {paddingBottom: insets.bottom + 10}]}>
            <IconButton source={icons.chatHeart} size={32} disabled={locationShared} onPress={onLocationPress} />
            <TextInput
                style={styles.messageInput}
                editable={false}
                multiline
                placeholder="Share location, then a photo, video or audio."
                placeholderTextColor="#344F7B"
            />
            <IconButton source={icons.camera} size={32} disabled={!locationShared} onPress={onCameraPress} />
            <IconButton source={icons.microphone} size={32} disabled={!locationShared} onPress={onMicrophonePress} />
        </View>
    );
}

export function RecordingBar({recorder, onFinish}: {
    recorder: AudioRecorder;
    onFinish: (uri: string | null) => void;
}) {
    const insets = useSafeAreaInsets();
    const {durationMillis} = useAudioRecorderState(recorder);
    const [stopping, setStopping] = useState(false);

    const stop = async (keep: boolean) => {
        setStopping(true);

        try {
            await recorder.stop();
            await setRecordingMode(false);
        } catch (error) {
            console.error('Failed to stop the recording:', error);
        }

        if (!keep && recorder.uri) {
            deleteMedia(recorder.uri);
        }

        onFinish(keep ? recorder.uri : null);
    };

    return (
        <View style={[styles.messageInputWrapper, {paddingBottom: insets.bottom + 10}]}>
            <IconButton source={icons.trash} size={28} disabled={stopping} onPress={() => void stop(false)} />
            <View style={styles.recording}>
                <View style={styles.recordingDot} />
                <Text style={styles.recordingTime}>{formatDuration(durationMillis / 1000)}</Text>
                <Text style={styles.recordingLabel}>Recording…</Text>
            </View>
            <IconButton
                source={icons.stop}
                size={32}
                color="#F34D47"
                disabled={stopping}
                onPress={() => void stop(true)}
            />
        </View>
    );
}

const styles = StyleSheet.create({
    // Both bars take turns in the same slot; sharing the wrapper keeps the swap from shifting the layout.
    messageInputWrapper: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        paddingTop: 10,
        paddingHorizontal: 10,
        backgroundColor: '#fff',
    },
    messageInput: {
        flex: 1,
        minHeight: 40,
        paddingHorizontal: 16,
        paddingVertical: 8,
        fontSize: 16,
        textAlignVertical: 'center',
        borderWidth: 1,
        borderColor: '#71829E',
        borderRadius: 4,
        backgroundColor: '#BFC8D6',
        opacity: 0.5,
    },
    recording: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        height: 40,
        paddingHorizontal: 8,
    },
    recordingDot: {
        width: 10,
        height: 10,
        borderRadius: 5,
        backgroundColor: '#F34D47',
    },
    recordingTime: {
        color: '#2C3038',
        fontSize: 16,
        fontVariant: ['tabular-nums'],
    },
    recordingLabel: {
        color: '#71829E',
        fontSize: 14,
    },
});
