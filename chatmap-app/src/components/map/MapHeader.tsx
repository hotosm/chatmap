import {Pressable, StyleSheet, View} from 'react-native';
import {Image} from 'expo-image';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

const logo = require('@/assets/images/chatmap-logo-gray.svg');

export function MapHeader({onLogoPress}: {onLogoPress: () => void}) {
    const insets = useSafeAreaInsets();

    return (
        <View style={[styles.header, {paddingTop: insets.top + 8}]}>
            <Pressable onPress={onLogoPress}>
                <Image source={logo} style={styles.headerLogo} />
            </Pressable>
        </View>
    );
}

const styles = StyleSheet.create({
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
});
