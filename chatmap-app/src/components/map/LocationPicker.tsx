import {useEffect, useRef, useState} from 'react';
import {Modal, Pressable, StyleSheet, Text, View} from 'react-native';
import {Image, type ImageProps} from 'expo-image';
import * as Location from 'expo-location';
import {WebView, type WebViewMessageEvent} from 'react-native-webview';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

const icons = {
    back: require('@/assets/icons/arrow-left.svg'),
    current: require('@/assets/icons/crosshair.svg'),
    pin: require('@/assets/icons/geo-alt.svg'),
};

const MAPLIBRE = 'https://unpkg.com/maplibre-gl@5.21.1/dist';

type Coordinates = {latitude: number; longitude: number};

type Fix =
    | {status: 'locating'}
    | {status: 'denied'}
    | {status: 'failed'}
    | {status: 'located'; coordinates: Coordinates; accuracy: number | null};

type PageMessage =
    | {type: 'ready'}
    | {type: 'center'; latitude: number; longitude: number}
    | {type: 'failed'};

async function locate(): Promise<Fix> {
    try {
        const {granted} = await Location.requestForegroundPermissionsAsync();
        if (!granted) {
            return {status: 'denied'};
        }

        const position = await Location.getCurrentPositionAsync({accuracy: Location.Accuracy.High});
        const {latitude, longitude, accuracy} = position.coords;

        return {status: 'located', coordinates: {latitude, longitude}, accuracy};
    } catch (error) {
        console.error('Failed to get location:', error);
        return {status: 'failed'};
    }
}

function fixDetail(fix: Fix): string {
    switch (fix.status) {
        case 'locating':
            return 'Locating…';
        case 'denied':
            return 'Location permission denied';
        case 'failed':
            return 'Could not get your location';
        case 'located':
            return fix.accuracy === null ? 'Located' : `Accurate to ${Math.round(fix.accuracy)} meters`;
    }
}

// The pin sits still over the center while the map moves under it, so the center is the chosen place.
// The map starts on the whole world and jumps to the GPS position when the app sends it, unless the user
// already moved it.
const PAGE = `<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<link rel="stylesheet" href="${MAPLIBRE}/maplibre-gl.css">
<style>
    html, body, #map { margin: 0; height: 100%; }
    #pin {
        position: absolute;
        left: 50%;
        top: 50%;
        width: 40px;
        height: 40px;
        margin: -40px 0 0 -20px;
        pointer-events: none;
        filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.4));
    }
    .position {
        width: 14px;
        height: 14px;
        border: 2px solid #fff;
        border-radius: 50%;
        background: #1A73E8;
        box-shadow: 0 0 3px rgba(0, 0, 0, 0.4);
    }
</style>
</head>
<body>
<div id="map"></div>
<svg id="pin" viewBox="0 0 16 16" fill="#F34D47">
    <path d="M8 16s6-5.686 6-10A6 6 0 0 0 2 6c0 4.314 6 10 6 10m0-7a3 3 0 1 1 0-6 3 3 0 0 1 0 6"/>
</svg>
<script>
    function send(message) {
        window.ReactNativeWebView.postMessage(JSON.stringify(message));
    }
</script>
<script src="${MAPLIBRE}/maplibre-gl.js" onerror="send({type: 'failed'})"></script>
<script>
    if (window.maplibregl) {
        const map = new maplibregl.Map({
            container: 'map',
            style: {
                version: 8,
                sources: {
                    osm: {
                        type: 'raster',
                        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                        tileSize: 256,
                        attribution: '&copy; OpenStreetMap contributors',
                        maxzoom: 19,
                    },
                },
                layers: [{id: 'osm', type: 'raster', source: 'osm'}],
            },
            center: [0, 0],
            zoom: 1,
            dragRotate: false,
            pitchWithRotate: false,
            touchPitch: false,
        });

        map.touchZoomRotate.disableRotation();

        const dot = document.createElement('div');
        dot.className = 'position';
        const position = new maplibregl.Marker({element: dot});
        let moved = false;

        map.on('dragstart', () => {
            moved = true;
        });
        map.on('zoomstart', (event) => {
            if (event.originalEvent) {
                moved = true;
            }
        });

        window.showPosition = (longitude, latitude) => {
            position.setLngLat([longitude, latitude]).addTo(map);

            if (!moved) {
                map.jumpTo({center: [longitude, latitude], zoom: 16});
            }
        };

        const report = () => {
            const center = map.getCenter().wrap();
            send({type: 'center', latitude: center.lat, longitude: center.lng});
        };

        map.on('load', () => {
            report();
            send({type: 'ready'});
        });
        map.on('moveend', report);
    }
</script>
</body>
</html>`;

function Option({icon, title, detail, disabled, onPress}: {
    icon: ImageProps['source'];
    title: string;
    detail: string;
    disabled: boolean;
    onPress: () => void;
}) {
    return (
        <Pressable disabled={disabled} onPress={onPress} style={[styles.option, disabled && styles.disabled]}>
            <Image source={icon} tintColor="#2C3038" style={styles.optionIcon} />
            <View style={styles.optionText}>
                <Text style={styles.optionTitle}>{title}</Text>
                <Text style={styles.optionDetail}>{detail}</Text>
            </View>
        </Pressable>
    );
}

export function LocationPicker({online, onClose, onPick}: {
    online: boolean;
    onClose: () => void;
    onPick: (latitude: number, longitude: number) => void;
}) {
    const insets = useSafeAreaInsets();
    const webViewRef = useRef<WebView>(null);
    const [fix, setFix] = useState<Fix>({status: 'locating'});
    const [mapShown, setMapShown] = useState(online);
    const [mapReady, setMapReady] = useState(false);
    const [mapFailed, setMapFailed] = useState(false);
    const [center, setCenter] = useState<Coordinates | null>(null);

    // Once the map is on screen it stays, even if the connection drops: the chosen place comes from the
    // map, not from the internet
    if (online && !mapShown) {
        setMapShown(true);
    }

    useEffect(() => {
        let active = true;

        locate().then((next) => {
            if (active) {
                setFix(next);
            }
        });

        return () => {
            active = false;
        };
    }, []);

    useEffect(() => {
        if (mapReady && fix.status === 'located') {
            const {latitude, longitude} = fix.coordinates;
            webViewRef.current?.injectJavaScript(`showPosition(${longitude}, ${latitude}); true;`);
        }
    }, [mapReady, fix]);

    const receive = (event: WebViewMessageEvent) => {
        const message: PageMessage = JSON.parse(event.nativeEvent.data);

        if (message.type === 'ready') {
            setMapReady(true);
        } else if (message.type === 'failed') {
            setMapFailed(true);
        } else {
            setCenter({latitude: message.latitude, longitude: message.longitude});
        }
    };

    const sendCurrent = () => {
        if (fix.status === 'located') {
            onPick(fix.coordinates.latitude, fix.coordinates.longitude);
        }
    };

    const sendSelected = () => {
        if (center) {
            onPick(center.latitude, center.longitude);
        }
    };

    let selectedDetail = 'Move the map to place the pin';
    if (!mapShown) {
        selectedDetail = 'Needs a connection';
    } else if (mapFailed) {
        selectedDetail = 'The map could not load';
    }

    return (
        <Modal animationType="slide" onRequestClose={onClose}>
            <View style={styles.picker}>
                <View style={[styles.header, {paddingTop: insets.top + 8}]}>
                    <Pressable hitSlop={8} onPress={onClose}>
                        <Image source={icons.back} tintColor="#2C3038" style={styles.backIcon} />
                    </Pressable>
                    <Text style={styles.title}>Send location</Text>
                </View>
                <View style={styles.map}>
                    {mapShown && !mapFailed ? (
                        <WebView
                            ref={webViewRef}
                            originWhitelist={['*']}
                            source={{html: PAGE}}
                            applicationNameForUserAgent="chatmap-app"
                            onMessage={receive}
                            onError={() => setMapFailed(true)}
                        />
                    ) : (
                        <Text style={styles.mapNotice}>
                            {mapFailed ? 'The map could not load.' : 'The map needs a connection.'}
                            {' '}You can still send your current location.
                        </Text>
                    )}
                </View>
                <View style={[styles.options, {paddingBottom: insets.bottom + 10}]}>
                    <Option
                        icon={icons.current}
                        title="Send your current location"
                        detail={fixDetail(fix)}
                        disabled={fix.status !== 'located'}
                        onPress={sendCurrent}
                    />
                    <Option
                        icon={icons.pin}
                        title="Send selected location"
                        detail={selectedDetail}
                        disabled={!mapShown || mapFailed || center === null}
                        onPress={sendSelected}
                    />
                </View>
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    picker: {
        flex: 1,
        backgroundColor: '#F7F8F9',
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 16,
        paddingHorizontal: 16,
        paddingBottom: 12,
        backgroundColor: '#fff',
    },
    backIcon: {
        width: 24,
        height: 24,
    },
    title: {
        color: '#2C3038',
        fontSize: 18,
        fontWeight: '600',
    },
    map: {
        flex: 1,
        justifyContent: 'center',
    },
    mapNotice: {
        paddingHorizontal: 24,
        color: '#71829E',
        fontSize: 14,
        textAlign: 'center',
    },
    options: {
        paddingTop: 4,
        backgroundColor: '#fff',
    },
    option: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 16,
        paddingHorizontal: 16,
        paddingVertical: 12,
    },
    optionIcon: {
        width: 24,
        height: 24,
    },
    optionText: {
        flex: 1,
        gap: 2,
    },
    optionTitle: {
        color: '#2C3038',
        fontSize: 16,
    },
    optionDetail: {
        color: '#71829E',
        fontSize: 13,
    },
    disabled: {
        opacity: 0.5,
    },
});
