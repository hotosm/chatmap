import {useRef, useState} from 'react';
import {Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View} from 'react-native';
import {Image, type ImageProps} from 'expo-image';
import {Stack} from 'expo-router';
import {CameraView, useCameraPermissions, type CameraCapturedPicture} from 'expo-camera';
import * as Location from 'expo-location';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

const logo = require('@/assets/images/chatmap-logo-gray.svg');

const icons = {
    save: require('@/assets/icons/save2.svg'),
    trash: require('@/assets/icons/trash-fill.svg'),
    translate: require('@/assets/icons/translate.svg'),
    chatHeart: require('@/assets/icons/chat-heart.svg'),
    camera: require('@/assets/icons/camera.svg'),
    close: require('@/assets/icons/x-lg.svg'),
};

type Message =
    | {id: number; type: 'LOCATION'; coordinates: number[]}
    | {id: number; type: 'MEDIA'; uri: string; width: number; height: number};

const tileHeaders = process.env.EXPO_OS === 'web' ? undefined : {'User-Agent': 'chatmap-app/1.0.0'};

const getTileURL = (lon: number, lat: number) => {
    const zoom = 18;
    const latTile = Math.floor((1 - Math.log(Math.tan(lat * Math.PI / 180) + 1 / Math.cos(lat * Math.PI / 180)) / Math.PI) / 2 * Math.pow(2, zoom));
    const lonTile = Math.floor((lon + 180) / 360 * Math.pow(2, zoom));
    return `https://tile.openstreetmap.org/${zoom}/${lonTile}/${latTile}.png`;
};

function IconButton({source, size, color = '#2C3038', disabled, onPress}: {
    source: ImageProps['source'];
    size: number;
    color?: string;
    disabled?: boolean;
    onPress?: () => void;
}) {
    return (
        <Pressable disabled={disabled} onPress={onPress} style={[styles.iconButton, disabled && styles.disabled]}>
            <Image source={source} tintColor={color} contentFit="contain" style={{width: size, height: size}} />
        </Pressable>
    );
}

function Header() {
    const insets = useSafeAreaInsets();

    return (
        <View style={[styles.header, {paddingTop: insets.top + 8}]}>
            <Image source={logo} style={styles.headerLogo} />
            <View style={styles.headerRest}>
                <Pressable style={styles.exportButton}>
                    <Image source={icons.save} tintColor="#000" style={styles.exportButtonIcon} />
                    <Text style={styles.exportButtonLabel}>Export</Text>
                </Pressable>
                <IconButton source={icons.trash} size={14} color="#000" />
                <IconButton source={icons.translate} size={16} />
            </View>
        </View>
    );
}

function LocationMessage({coordinates}: {coordinates: number[]}) {
    return (
        <View style={styles.message}>
            <Image source={{uri: getTileURL(coordinates[0], coordinates[1]), headers: tileHeaders}} style={styles.messageImage} />
            <View style={styles.locationPin}>
                <View style={styles.locationPinHead} />
                <View style={styles.locationPinStem} />
            </View>
        </View>
    );
}

function MediaMessage({uri, width, height}: {uri: string; width: number; height: number}) {
    return (
        <View style={styles.message}>
            <Image source={{uri}} style={[styles.messageImage, {aspectRatio: width / height}]} />
        </View>
    );
}

function MessageInputBar({locationShared, onLocationPress, onCameraPress}: {
    locationShared: boolean;
    onLocationPress: () => void;
    onCameraPress: () => void;
}) {
    const insets = useSafeAreaInsets();

    return (
        <View style={[styles.messageInputWrapper, {paddingBottom: insets.bottom + 10}]}>
            <IconButton source={icons.chatHeart} size={32} disabled={locationShared} onPress={onLocationPress} />
            <TextInput
                style={styles.messageInput}
                editable={false}
                placeholder="Share location, then picture. Repeat."
                placeholderTextColor="#344F7B"
            />
            <IconButton source={icons.camera} size={32} disabled={!locationShared} onPress={onCameraPress} />
        </View>
    );
}

function CameraModal({onClose, onPicture}: {
    onClose: () => void;
    onPicture: (picture: CameraCapturedPicture) => void;
}) {
    const insets = useSafeAreaInsets();
    const cameraRef = useRef<CameraView>(null);
    const [cameraReady, setCameraReady] = useState(false);

    const takePicture = async () => {
        try {
            const picture = await cameraRef.current?.takePictureAsync();
            if (picture) {
                onPicture(picture);
            }
        } catch (error) {
            console.error('Error getting the picture', error);
        }
    };

    return (
        <Modal animationType="slide" onRequestClose={onClose}>
            <View style={styles.camera}>
                <CameraView
                    ref={cameraRef}
                    style={StyleSheet.absoluteFill}
                    facing="back"
                    onCameraReady={() => setCameraReady(true)}
                />
                <Pressable onPress={onClose} style={[styles.cameraClose, {top: insets.top + 12}]}>
                    <Image source={icons.close} tintColor="#fff" style={styles.cameraCloseIcon} />
                </Pressable>
                <View style={[styles.cameraControls, {paddingBottom: insets.bottom + 24}]}>
                    <Pressable
                        onPress={takePicture}
                        disabled={!cameraReady}
                        style={[styles.shutter, !cameraReady && styles.disabled]}
                    >
                        <View style={styles.shutterInner} />
                    </Pressable>
                </View>
            </View>
        </Modal>
    );
}

export default function MapperScreen() {
    const insets = useSafeAreaInsets();
    const scrollRef = useRef<ScrollView>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [locationShared, setLocationShared] = useState(false);
    const [cameraOpen, setCameraOpen] = useState(false);
    const [, requestCameraPermission] = useCameraPermissions();

    const shareLocation = async () => {
        try {
            const {granted} = await Location.requestForegroundPermissionsAsync();
            if (!granted) {
                console.error('Location permission denied');
                return;
            }

            const position = await Location.getCurrentPositionAsync({accuracy: Location.Accuracy.High});
            const {latitude, longitude} = position.coords;

            setMessages((prev) => [...prev, {id: prev.length, type: 'LOCATION', coordinates: [longitude, latitude]}]);
            setLocationShared(true);
        } catch (error) {
            console.error('Failed to get location:', error);
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

    const addPicture = ({uri, width, height}: CameraCapturedPicture) => {
        setMessages((prev) => [...prev, {id: prev.length, type: 'MEDIA', uri, width, height}]);
        setLocationShared(false);
        setCameraOpen(false);
    };

    return (
        <View style={styles.mapper}>
            <Stack.Screen options={{headerShown: false}} />
            <ScrollView
                ref={scrollRef}
                contentContainerStyle={[styles.messages, {paddingTop: insets.top + 70}]}
                onContentSizeChange={() => scrollRef.current?.scrollToEnd()}
            >
                {messages.map((message) => (
                    message.type === 'LOCATION' ?
                        <LocationMessage key={message.id} coordinates={message.coordinates} /> :
                        <MediaMessage key={message.id} uri={message.uri} width={message.width} height={message.height} />
                ))}
            </ScrollView>
            <Header />
            <MessageInputBar
                locationShared={locationShared}
                onLocationPress={shareLocation}
                onCameraPress={openCamera}
            />
            {cameraOpen && <CameraModal onClose={() => setCameraOpen(false)} onPicture={addPicture} />}
        </View>
    );
}

const styles = StyleSheet.create({
    mapper: {
        flex: 1,
        backgroundColor: '#F7F8F9',
    },
    header: {
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 20,
        paddingBottom: 8,
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
    },
    headerLogo: {
        width: 36,
        height: 36,
    },
    headerRest: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 20,
        paddingLeft: 12,
    },
    exportButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        height: 30,
        paddingLeft: 8,
        paddingRight: 12,
    },
    exportButtonIcon: {
        width: 14,
        height: 14,
    },
    exportButtonLabel: {
        color: '#000',
        fontSize: 14,
        fontWeight: '600',
    },
    iconButton: {
        padding: 8,
    },
    disabled: {
        opacity: 0.5,
    },
    messages: {
        paddingHorizontal: 20,
        paddingBottom: 10,
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
        height: 40,
        paddingHorizontal: 16,
        fontSize: 16,
        borderWidth: 1,
        borderColor: '#71829E',
        borderRadius: 4,
        backgroundColor: '#BFC8D6',
        opacity: 0.5,
    },
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
    cameraControls: {
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: 0,
        alignItems: 'center',
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
});
