import {useState} from 'react';
import {StyleSheet, Text, TextInput, View} from 'react-native';
import {router, Stack, useLocalSearchParams} from 'expo-router';

import {Button} from '../components/Button';
import {joinMap, type JoinOutcome} from '../contributor/join';
import {getDatabase} from '../storage/database';
import {addMap} from '../storage/maps';

async function saveJoinedMap(mapId: string, mapName: string | null, nickname: string): Promise<void> {
    try {
        await addMap(await getDatabase(), {mapId, mapName, nickname});
    } catch (error) {
        console.warn('Saving the joined map failed', error);
    }
}

function Message({text}: {text: string}) {
    return <Text style={styles.message}>{text}</Text>;
}

function DoneButton() {
    return <Button label="Done" onPress={() => router.replace('/')}/>;
}

function Result({outcome}: {outcome: JoinOutcome}) {
    switch (outcome.status) {
        case 'joined':
            return <Message text={`You joined ${outcome.map.mapName ?? 'Untitled map'}.`}/>;
        case 'already-member':
            return <Message text={`You are already a contributor of ${outcome.map.mapName ?? 'Untitled map'}.`}/>;
        case 'invalid-invitation':
            return <Message text="This invitation is no longer valid. Ask the map owner for a new QR."/>;
        case 'removed':
            return <Message text="You were removed from this map."/>;
    }
}

export default function JoinScreen() {
    const params = useLocalSearchParams<{token?: string}>();
    const token = typeof params.token === 'string' ? params.token : null;
    const [nickname, setNickname] = useState('');
    const [sending, setSending] = useState(false);
    const [failed, setFailed] = useState(false);
    const [outcome, setOutcome] = useState<JoinOutcome | null>(null);

    async function onJoin() {
        if (!token) {
            return;
        }

        setSending(true);
        setFailed(false);

        try {
            const result = await joinMap(token, nickname.trim());

            if (result.status === 'joined') {
                await saveJoinedMap(result.map.mapId, result.map.mapName, nickname.trim());
            }

            setOutcome(result);
        } catch {
            setFailed(true);
        } finally {
            setSending(false);
        }
    }

    if (!token) {
        return (
            <View style={styles.container}>
                <Stack.Screen options={{title: 'Join a map'}}/>
                <Result outcome={{status: 'invalid-invitation'}}/>
                <DoneButton/>
            </View>
        );
    }

    if (outcome) {
        return (
            <View style={styles.container}>
                <Stack.Screen options={{title: 'Join a map'}}/>
                <Result outcome={outcome}/>
                <DoneButton/>
            </View>
        );
    }

    const canJoin = nickname.trim().length > 0 && !sending;

    return (
        <View style={styles.container}>
            <Stack.Screen options={{title: 'Join a map'}}/>
            <Text style={styles.label}>Choose a nickname</Text>
            <TextInput
                value={nickname}
                onChangeText={setNickname}
                placeholder="Your nickname"
                autoCapitalize="words"
                editable={!sending}
                style={styles.input}
            />
            {failed && <Text style={styles.error}>Could not join. Check your connection and try again.</Text>}
            <Button label="Join" onPress={onJoin} disabled={!canJoin} loading={sending}/>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        justifyContent: 'center',
        padding: 24,
        gap: 12,
    },
    label: {
        color: '#2C3038',
        fontSize: 16,
        fontWeight: '600',
    },
    input: {
        height: 44,
        paddingHorizontal: 12,
        borderWidth: 1,
        borderColor: '#C4C3C5',
        borderRadius: 8,
        fontSize: 16,
    },
    message: {
        color: '#2C3038',
        fontSize: 16,
        textAlign: 'center',
    },
    error: {
        color: '#B00020',
        fontSize: 14,
    },
});
