import type {ConfigContext, ExpoConfig} from 'expo/config';

// One installable app per build flow, so they can live side by side on a phone,
// each with its own local data. The production identity stays in app.json.
const VARIANTS = {
    production: {nameSuffix: '', packageSuffix: ''},
    development: {nameSuffix: ' Dev', packageSuffix: '.dev'},
    local: {nameSuffix: ' Local', packageSuffix: '.local'},
};

type Variant = keyof typeof VARIANTS;

function currentVariant(): Variant {
    const value = process.env.APP_VARIANT || 'production';

    if (!(value in VARIANTS)) {
        throw new Error(`Unknown APP_VARIANT "${value}". Use one of: ${Object.keys(VARIANTS).join(', ')}.`);
    }

    return value as Variant;
}

export default ({config}: ConfigContext): ExpoConfig => {
    const variant = VARIANTS[currentVariant()];

    return {
        ...config,
        name: `${config.name}${variant.nameSuffix}`,
        slug: config.slug ?? 'chatmap',
        ios: {
            ...config.ios,
            bundleIdentifier: `${config.ios?.bundleIdentifier}${variant.packageSuffix}`,
        },
        android: {
            ...config.android,
            package: `${config.android?.package}${variant.packageSuffix}`,
        },
    };
};
