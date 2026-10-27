import {Alert, FlatList, Pressable, RefreshControl, StyleSheet, Text, View} from 'react-native';
import {router, Stack} from 'expo-router';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {Button} from '../components/Button';
import {useConnectivity} from '../connectivity/connectivity';
import {useMaps} from '../hooks/useMaps';
import type {StoredMap} from '../storage/maps';

function MapItem({map}: {map: StoredMap}) {
    return (
        <Pressable
            onPress={() => router.push({pathname: '/map/[id]', params: {id: map.mapId}})}
            style={styles.item}
        >
            <Text style={styles.itemName}>{map.mapName ?? 'Untitled map'}</Text>
            <Text style={styles.itemNickname}>Contributing as {map.nickname}</Text>
        </Pressable>
    );
}

function EmptyList() {
    return (
        <View style={styles.empty}>
            <Text style={styles.emptyTitle}>No maps yet</Text>
            <Text style={styles.emptyMessage}>Scan an invitation from the map owner to start contributing.</Text>
        </View>
    );
}

export default function HomeScreen() {
    const insets = useSafeAreaInsets();
    const {maps, refreshedAt, loaded, refreshing, failed, refresh} = useMaps();
    const offline = useConnectivity() === 'offline';

    function onScan() {
        if (offline) {
            Alert.alert('You are offline', 'You need a connection to join a map.');
            return;
        }

        router.push('/scan');
    }

    return (
        <View style={styles.container}>
            <Stack.Screen options={{title: 'ChatMap'}}/>
            <FlatList
                data={maps}
                keyExtractor={(map) => map.mapId}
                renderItem={({item}) => <MapItem map={item}/>}
                refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh}/>}
                ListEmptyComponent={loaded ? <EmptyList/> : null}
                ListHeaderComponent={
                    offline ? (
                        <Text style={styles.offline}>You are offline. Showing the last saved list.</Text>
                    ) : failed ? (
                        <Text style={styles.warning}>Could not refresh the list. Showing the last saved copy.</Text>
                    ) : null
                }
                ListFooterComponent={loaded ? (
                    <Text style={styles.footer}>
                        {refreshedAt ? `Updated ${refreshedAt.toLocaleString()}` : 'Not updated yet'}
                    </Text>
                ) : null}
                contentContainerStyle={styles.list}
            />
            <View style={[styles.actions, {paddingBottom: insets.bottom + 16}]}>
                {/* Only dimmed, not disabled: pressing it offline explains why joining is not possible */}
                <Button label="Scan invitation" onPress={onScan} style={offline && styles.scanButtonOffline}/>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F7F8F9',
    },
    list: {
        flexGrow: 1,
        padding: 16,
        gap: 12,
    },
    item: {
        padding: 16,
        borderRadius: 8,
        backgroundColor: '#fff',
        boxShadow: '1px 1px 0px rgba(0, 0, 0, 0.05)',
    },
    itemName: {
        color: '#2C3038',
        fontSize: 16,
        fontWeight: '600',
    },
    itemNickname: {
        marginTop: 4,
        color: '#71829E',
        fontSize: 14,
    },
    empty: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
    },
    emptyTitle: {
        color: '#2C3038',
        fontSize: 18,
        fontWeight: '600',
    },
    emptyMessage: {
        marginTop: 8,
        color: '#71829E',
        fontSize: 14,
        textAlign: 'center',
    },
    warning: {
        color: '#B00020',
        fontSize: 14,
    },
    offline: {
        color: '#71829E',
        fontSize: 14,
    },
    footer: {
        marginTop: 4,
        color: '#71829E',
        fontSize: 12,
        textAlign: 'center',
    },
    actions: {
        paddingHorizontal: 16,
        paddingTop: 12,
        backgroundColor: '#fff',
    },
    scanButtonOffline: {
        opacity: 0.5,
    },
});
