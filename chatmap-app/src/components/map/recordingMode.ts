import {setAudioModeAsync} from 'expo-audio';

// Android replaces the whole audio mode on every call, and a field left out ends up false.
export function setRecordingMode(allowsRecording: boolean) {
    return setAudioModeAsync({allowsRecording, playsInSilentMode: true});
}
