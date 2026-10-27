import {useState} from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {CameraView, useCameraPermissions} from 'expo-camera';
import {router, Stack} from 'expo-router';

import {Button} from '../components/Button';
import {parseInvitation} from '../contributor/invitation';

export default function ScanScreen() {
    const [permission, requestPermission] = useCameraPermissions();
    const [scanned, setScanned] = useState(false);
    const [invalid, setInvalid] = useState(false);

    if (!permission) {
        return <View style={styles.container}/>;
    }

    if (!permission.granted) {
        return (
            <View style={styles.container}>
                <Stack.Screen options={{title: 'Join a map'}}/>
                <Text style={styles.message}>Camera access is needed to scan an invitation.</Text>
                <Button label="Allow camera" onPress={requestPermission}/>
            </View>
        );
    }

    function onBarcodeScanned({data}: {data: string}) {
        setScanned(true);
        const token = parseInvitation(data);

        if (!token) {
            setInvalid(true);
            return;
        }

        router.replace({pathname: '/join', params: {token}});
    }

    function onRetry() {
        setInvalid(false);
        setScanned(false);
    }

    return (
        <View style={styles.container}>
            <Stack.Screen options={{title: 'Join a map'}}/>
            <CameraView
                style={StyleSheet.absoluteFill}
                barcodeScannerSettings={{barcodeTypes: ['qr']}}
                onBarcodeScanned={scanned ? undefined : onBarcodeScanned}
            />
            {invalid && (
                <View style={styles.overlay}>
                    <Text style={styles.message}>This code is not a ChatMap invitation.</Text>
                    <Button label="Scan again" onPress={onRetry}/>
                </View>
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
    },
    overlay: {
        position: 'absolute',
        bottom: 48,
        padding: 16,
        borderRadius: 8,
        backgroundColor: '#fff',
        alignItems: 'center',
    },
    message: {
        color: '#2C3038',
        fontSize: 16,
        textAlign: 'center',
        marginBottom: 12,
    },
});
