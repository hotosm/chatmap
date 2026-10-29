# chatmap-app

ChatMap's mobile app (Expo / React Native). This document explains how to make
a build in each of the three flows. The steps are written for Android; what
changes on iOS is in [iOS](#ios).

## The three flows

| Flow | Server | EAS profile | Installed app | ID (Android and iOS) |
|---|---|---|---|---|
| Local | backend on the machine (`.env.local` or ngrok tunnel) | `local-devclient` (dev client) or `local-standalone` (JavaScript bundled in, via ngrok) | chatmap-app Local | `com.anonymous.chatmapapp.local` |
| Development | `https://dev.chatmap.hotosm.org/` | `development` | chatmap-app Dev | `com.anonymous.chatmapapp.dev` |
| Production | `https://chatmap.hotosm.org/` | `production-store` (Play Store) or `production-direct` (APK) | chatmap-app | `com.anonymous.chatmapapp` |

Each flow is a separate app, on Android and on iOS. All three can be installed
on the same phone, and each one keeps its own maps, its Points queue and its
secrets. That way the data from one server never mixes with another's.

### How the API URL reaches the app

The app takes the server from `EXPO_PUBLIC_API_URL`. This variable is written
into the JavaScript when it is compiled; it isn't read when the app opens. That
defines how each flow works:

- **Development, Production and `local-standalone`** carry the JavaScript
  inside the APK. The URL comes from the EAS variables at build time. Changing
  servers requires a new build.
- **`local-devclient`** is a *development build* (dev client). That binary
  doesn't include the JavaScript: it requests it from Metro on the machine, and
  Metro reads `.env.local` every time it starts.

If `EXPO_PUBLIC_API_URL` isn't defined, the app closes when it opens
(`src/config.ts`).

### How the variant is chosen

`app.config.ts` reads `APP_VARIANT` (`local`, `development` or `production`) and
adds a suffix to the name, to the Android `package` and to the iOS
`bundleIdentifier` in `app.json`. Each
`eas.json` profile defines its `APP_VARIANT`, and `npm start` uses `local`.
Without `APP_VARIANT`, the variant is `production`.

## Before any build

1. Install the dependencies with `npm install`.
2. Log in to EAS with an account that has access to the
   `@lawal-coop/chatmap` project: `npx eas-cli@latest login`. To see the
   current session: `npx eas-cli@latest whoami`.
3. Run the checks:

   ```bash
   npx expo-doctor            # project dependencies and config
   npx expo install --check   # packages whose version differs from the SDK's (--fix corrects them)
   npx tsc --noEmit           # types
   npx expo lint              # lint
   ```

For Development and Production it is also worth compiling the production
JavaScript with the server URL. That way bundling errors show up in seconds
instead of at the end of an EAS build:

```bash
EXPO_PUBLIC_API_URL=https://dev.chatmap.hotosm.org/ npx expo export --platform android --output-dir /tmp/chatmap-export
```

The first time a build is made for a new `package`, EAS asks whether to
generate a keystore to sign the app. Accept: EAS stores it and uses it for the
following builds.

## Local

The backend runs on the machine and the app uses a dev client. The JavaScript
reloads live, and the binary is only rebuilt when something native changes.

1. Start the backend with `compose.dev.yml`. The API runs on port 8000.
2. Create `.env.local` from `.env.example`:

   ```
   EXPO_PUBLIC_API_URL=http://localhost:8000
   ```

3. Connect the phone over USB and forward the port:

   ```bash
   adb reverse tcp:8000 tcp:8000
   ```

   On the phone, `localhost` is the phone itself. This command makes its port
   8000 point to the machine's. It has to be repeated every time the phone is
   disconnected or `adb` restarts.

4. Install the dev client, the first time or when something native changes:

   ```bash
   npx eas-cli@latest build --profile local-devclient --platform android
   ```

   When it finishes, EAS shows a link and a QR to install the APK. It can also
   be built on the machine with `npm run android`, which needs Android Studio
   and the Android SDK.

5. Start Metro and open the **chatmap-app Local** app:

   ```bash
   npm start
   ```

   Use `npm start` and not `npx expo start`: the script sets
   `APP_VARIANT=local`, and without it Expo looks for the production app when
   opening it from the terminal. The scripts use the Linux and macOS
   `APP_VARIANT=local ...` syntax.

The dev client has to be rebuilt when:

- a package with native code is added or removed;
- plugins, permissions or other native config change in `app.json` or
  `app.config.ts`;
- Expo is updated, even a patch with `npx expo install --fix`.

If you build with `npm run android` and an `android/` folder generated earlier
already exists, regenerate it first:

```bash
APP_VARIANT=local npx expo prebuild --clean --platform android
```

To test the dev client against the dev server without making a build, it is
enough to set `EXPO_PUBLIC_API_URL=https://dev.chatmap.hotosm.org/` in
`.env.local` and restart Metro.

### Local with the JavaScript bundled in

Useful to test the app as a user sees it, but against the local backend. EAS
doesn't receive `.env.local`, so the backend is exposed with a fixed-URL ngrok
tunnel, and that URL is written into the build: if it changes, a new build is
needed.

1. Start the backend with `compose.dev.yml` and the ngrok tunnel to port 8000.
2. The first time, load the tunnel URL into the EAS `preview` environment:

   ```bash
   npx eas-cli@latest env:set --name EXPO_PUBLIC_API_URL --value <tunnel-url> --environment preview --visibility plaintext
   ```

   The URL doesn't go in the repo: with it, anyone can reach the local backend
   while the tunnel is open.

3. Start the build:

   ```bash
   npx eas-cli@latest build --profile local-standalone --platform android
   ```

4. Install the APK from the link or the QR that EAS shows. It installs as
   **chatmap-app Local**, the same app as the dev client: installing one
   replaces the other and keeps the data, because both talk to the same backend.

## Development

A build with the JavaScript bundled in, against
`https://dev.chatmap.hotosm.org/`, to test the app as a user sees it.

1. Run the checks in [Before any build](#before-any-build).
2. Start the build:

   ```bash
   npx eas-cli@latest build --profile development --platform android
   ```

3. Install the APK from the link or the QR that EAS shows. It installs as
   **chatmap-app Dev**.

EAS bumps the `versionCode` on every build, so the new APK installs as an update
of the previous one and the data isn't lost.

## Production

Against `https://chatmap.hotosm.org/`. There are two profiles for the same app:
`production-store` generates an `.aab` for Play Store and `production-direct`
generates an `.apk` to install directly.

### Before the first production build

- **Set the final `package`** in `app.json` (`android.package`). Today it is
  `com.anonymous.chatmapapp`, a template value. Once published on Play Store it
  can't be changed: changing it creates another app. The Dev and Local variants
  take that same value with their suffix.
- **Pick one channel per user.** Play Store re-signs the app with its own key
  (Play App Signing). That is why an app installed from Play Store can't be
  updated with the direct APK, or the other way around. Switching channels
  requires uninstalling, and the local data is lost.

### Making a new version

1. Bump `version` in `app.json`, for example from `1.0.0` to `1.1.0`. It is the
   version the user sees. EAS bumps the `versionCode` on every build.
2. Run the checks in [Before any build](#before-any-build).
3. Start the build for the channel.

   Play Store:

   ```bash
   npx eas-cli@latest build --profile production-store --platform android
   npx eas-cli@latest submit --profile production-store --platform android --latest
   ```

   `submit` uploads the latest `.aab` to Play Console. It needs a Google
   service account key. The app's first upload to Play Console has to be
   manual.

   Direct APK:

   ```bash
   npx eas-cli@latest build --profile production-direct --platform android
   ```

   EAS shows a link to download the `.apk`.

## iOS

The profiles are the same as on Android, with `--platform ios`. Two things
change: signing depends on an Apple Developer account, and a direct-install
build only installs on the iPhones registered in that account.

### Apple account and bundle ID

For now, iOS builds are signed with a temporary Apple account, to test the
beta. That is why the `bundleIdentifier` in `app.json` is
`com.anonymous.chatmapapp`, a provisional value.

The bundle ID is unique across all of Apple, and it stays with the account that
registers it. If a build with that ID is uploaded to App Store Connect
(TestFlight or App Store), the ID is tied to that account and can't be used in
another one, even if the app is deleted. That is why:

- With the temporary account, only the direct-install profiles are used on
  iOS. Not `production-store`, because it goes through App Store Connect.
- The final bundle ID is registered only by the account that will publish.

When the publishing account takes over:

1. Put the final bundle ID in `app.json` (`ios.bundleIdentifier`). The Dev and
   Local variants take that value with their suffix.
2. Start the build with that account. EAS asks to log in to Apple and generates
   that account's certificate and signing profiles.
3. The temporary account's credentials stay stored in EAS. They can be deleted
   from the project's Credentials section on expo.dev.

### Registering iPhones

A direct-install build carries the list of iPhones that can install it. Each
iPhone is registered before the build:

1. Run:

   ```bash
   npx eas-cli@latest device:create
   ```

   It asks to log in to Apple to know which account to register it in. Choose
   **Website**: EAS shows a link and a QR.

2. Send the link to the person who will test. They have to open it on the
   iPhone with **Safari**; other browsers may fail.
3. On the iPhone: Settings → Profile Downloaded → Install. That profile only
   passes the iPhone's identifier (UDID) to EAS.

To see the registered iPhones: `npx eas-cli@latest device:list`.

- An iPhone registered after a build can't install that build: a new one is
  needed.
- Apple allows up to 100 iPhones per year on each account.
- With a newly created or renewed Apple account, Apple can take between 24 and
  72 hours to accept a new iPhone, and the first build that includes it may
  fail.

### Direct-install build

1. Run the checks in [Before any build](#before-any-build).
2. Start the build:

   ```bash
   npx eas-cli@latest build --profile production-direct --platform ios
   ```

   The first time, it asks to log in to Apple and creates the distribution
   certificate and the signing profile with the registered iPhones. EAS stores
   them for the following builds. If there are registered iPhones that aren't
   in the profile, it asks which ones to include and updates it.

3. Share the link EAS shows. It is opened on the iPhone with Safari and installs
   **chatmap-app**.
4. On iOS 16 or newer, the first time you have to turn on developer mode: open
   the app, go to Settings → Privacy & Security → Developer Mode, turn it on and
   restart the iPhone. Without it the app doesn't open.

### The other profiles

- `development` and `local-standalone` work the same as `production-direct`:
  change the profile in the command, and they only install on registered
  iPhones.
- `local-devclient` is also built on EAS with `--platform ios`. Building it on
  the machine needs a Mac with Xcode. The iPhone has no `adb reverse`, so in
  `.env.local` it is better to use the ngrok tunnel URL.

## Environment variables in EAS

| EAS environment | Profiles | `EXPO_PUBLIC_API_URL` |
|---|---|---|
| `development` | `local-devclient`, `development` | `https://dev.chatmap.hotosm.org/` |
| `preview` | `local-standalone` | ngrok tunnel URL (not in the repo) |
| `production` | `production-store`, `production-direct` | `https://chatmap.hotosm.org/` |

The `local-devclient` profile declares the `development` environment, but the
dev client doesn't carry the JavaScript, so that URL isn't used: the app takes
the one in `.env.local`. The `preview` environment is used for
`local-standalone` because EAS only has three fixed environments and it was the
free one.

```bash
npx eas-cli@latest env:list --environment development
npx eas-cli@latest env:set --name EXPO_PUBLIC_API_URL --value <url> --environment development --visibility plaintext
```

A change to a variable only takes effect on the next build. The optional
connection detection variables (`EXPO_PUBLIC_HEALTH_*`, in `.env.example`) are
loaded the same way if they need to be changed.

## What gets uploaded to EAS

`.easignore`, at the repo root, makes EAS upload only `chatmap-app/` and not the
whole monorepo. For EAS, that file replaces every `.gitignore`: a new rule in
`chatmap-app/.gitignore` also has to be copied there. To see exactly what gets
uploaded:

```bash
npx eas-cli@latest build:inspect --platform android --profile development --stage archive --output /tmp/eas-archive
```

## Common problems

- **The app closes as soon as it opens.** `EXPO_PUBLIC_API_URL` is missing. In
  Local, check `.env.local` and restart Metro. In a build, check `env:list` for
  the profile's environment.
- **In Local the app doesn't reach the server.** Check that the backend is
  running and run `adb reverse tcp:8000 tcp:8000` again. With
  `local-standalone`, check that the ngrok tunnel is open.
- **When scanning an invitation QR with the camera, Android asks which app to
  open it with.** The three apps share the `hot-chatmap://` scheme. Choose the
  one for the server that generated the invitation. Scanning from inside the app
  doesn't have this problem.
