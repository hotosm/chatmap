import {ActivityIndicator, Pressable, StyleSheet, Text, type StyleProp, type ViewStyle} from 'react-native';

export function Button({label, onPress, disabled, loading, style}: {
    label: string;
    onPress: () => void;
    disabled?: boolean;
    loading?: boolean;
    style?: StyleProp<ViewStyle>;
}) {
    return (
        <Pressable onPress={onPress} disabled={disabled} style={[styles.button, disabled && styles.disabled, style]}>
            {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.label}>{label}</Text>}
        </Pressable>
    );
}

const styles = StyleSheet.create({
    button: {
        height: 44,
        paddingHorizontal: 20,
        borderRadius: 8,
        backgroundColor: '#2C3038',
        alignItems: 'center',
        justifyContent: 'center',
    },
    label: {
        color: '#fff',
        fontSize: 14,
        fontWeight: '600',
    },
    disabled: {
        opacity: 0.5,
    },
});
