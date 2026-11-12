import {Pressable, StyleSheet} from 'react-native';
import {Image, type ImageProps} from 'expo-image';

export function IconButton({source, size, color = '#2C3038', disabled, onPress}: {
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

const styles = StyleSheet.create({
    iconButton: {
        padding: 8,
    },
    disabled: {
        opacity: 0.5,
    },
});
