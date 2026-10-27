# chatmap-app

App móvil de ChatMap (Expo / React Native). Este documento explica cómo hacer
un build en cada uno de los tres flujos. Por ahora cubre solo Android.

## Los tres flujos

| Flujo | Servidor | Perfil de EAS | App instalada | Package |
|---|---|---|---|---|
| Local | backend en la máquina (`http://localhost:8000`) | `local` | chatmap-app Local | `com.anonymous.chatmapapp.local` |
| Development | `https://dev.chatmap.hotosm.org/` | `development` | chatmap-app Dev | `com.anonymous.chatmapapp.dev` |
| Production | `https://chatmap.hotosm.org/` | `production` (Play Store) o `production-apk` (APK) | chatmap-app | `com.anonymous.chatmapapp` |

Cada flujo es una app distinta para Android. Las tres se pueden instalar en el
mismo teléfono, y cada una guarda sus propios mapas, su cola de Points y sus
secretos. Así los datos de un servidor nunca se mezclan con los de otro.

### Cómo llega la URL de la API a la app

La app toma el servidor de `EXPO_PUBLIC_API_URL`. Esta variable queda escrita
en el JavaScript al momento de compilarlo; no se lee al abrir la app. Eso define
cómo funciona cada flujo:

- **Development y Production** llevan el JavaScript adentro del APK. La URL sale
  de las variables de EAS al hacer el build. Para cambiar de servidor hace falta
  un build nuevo.
- **Local** usa un *development build* (dev client). Ese binario no trae el
  JavaScript: lo pide a Metro en la máquina, y Metro lee `.env.local` cada vez
  que arranca.

Si `EXPO_PUBLIC_API_URL` no está definida, la app se cierra al abrir
(`src/config.ts`).

### Cómo se elige la variante

`app.config.ts` lee `APP_VARIANT` (`local`, `development` o `production`) y le
agrega un sufijo al nombre y al `package` que están en `app.json`. Cada perfil
de `eas.json` define su `APP_VARIANT`, y `npm start` usa `local`. Sin
`APP_VARIANT`, la variante es `production`.

## Antes de cualquier build

1. Instalar las dependencias con `npm install`.
2. Iniciar sesión en EAS con una cuenta que tenga acceso al proyecto
   `@lawal-coop/chatmap`: `npx eas-cli@latest login`. Para ver la sesión
   actual: `npx eas-cli@latest whoami`.
3. Correr los chequeos:

   ```bash
   npx expo-doctor            # dependencias y config del proyecto
   npx expo install --check   # paquetes con versión distinta a la del SDK (--fix los corrige)
   npx tsc --noEmit           # tipos
   npx expo lint              # lint
   ```

Para Development y Production conviene además compilar el JavaScript de
producción con la URL del servidor. Así los errores de bundling aparecen en
segundos y no al final de un build en EAS:

```bash
EXPO_PUBLIC_API_URL=https://dev.chatmap.hotosm.org/ npx expo export --platform android --output-dir /tmp/chatmap-export
```

La primera vez que se hace un build de un `package` nuevo, EAS pregunta si
genera un keystore para firmar la app. Hay que aceptar: EAS lo guarda y lo usa
en los builds siguientes.

## Local

El backend corre en la máquina y la app usa un dev client. El JavaScript se
recarga en vivo, y el binario solo se vuelve a compilar cuando cambia algo
nativo.

1. Levantar el backend con `compose.dev.yml`. La API queda en el puerto 8000.
2. Crear `.env.local` a partir de `.env.example`:

   ```
   EXPO_PUBLIC_API_URL=http://localhost:8000
   ```

3. Conectar el teléfono por USB y redirigir el puerto:

   ```bash
   adb reverse tcp:8000 tcp:8000
   ```

   En el teléfono, `localhost` es el propio teléfono. Este comando hace que su
   puerto 8000 apunte al de la máquina. Hay que repetirlo cada vez que se
   desconecta el teléfono o se reinicia `adb`.

4. Instalar el dev client, la primera vez o cuando cambia algo nativo:

   ```bash
   npx eas-cli@latest build --profile local --platform android
   ```

   Al terminar, EAS muestra un link y un QR para instalar el APK. También se
   puede compilar en la máquina con `npm run android`, que necesita Android
   Studio y el SDK de Android.

5. Arrancar Metro y abrir la app **chatmap-app Local**:

   ```bash
   npm start
   ```

   Hay que usar `npm start` y no `npx expo start`: el script define
   `APP_VARIANT=local`, y sin eso Expo busca la app de producción al abrirla
   desde la terminal. Los scripts usan la sintaxis `APP_VARIANT=local ...` de
   Linux y macOS.

Hay que volver a compilar el dev client cuando:

- se agrega o se quita un paquete con código nativo;
- cambian plugins, permisos u otra config nativa en `app.json` o
  `app.config.ts`;
- se actualiza Expo, incluso un parche con `npx expo install --fix`.

Si se compila con `npm run android` y ya existe una carpeta `android/`
generada antes, hay que regenerarla primero:

```bash
APP_VARIANT=local npx expo prebuild --clean --platform android
```

Para probar el dev client contra el servidor de dev sin hacer un build, alcanza
con poner `EXPO_PUBLIC_API_URL=https://dev.chatmap.hotosm.org/` en `.env.local`
y reiniciar Metro.

## Development

Build con el JavaScript adentro, contra `https://dev.chatmap.hotosm.org/`, para
probar la app como la ve un usuario.

1. Correr los chequeos de [Antes de cualquier build](#antes-de-cualquier-build).
2. Lanzar el build:

   ```bash
   npx eas-cli@latest build --profile development --platform android
   ```

3. Instalar el APK desde el link o el QR que muestra EAS. Se instala como
   **chatmap-app Dev**.

EAS sube el `versionCode` en cada build, así que el APK nuevo se instala como
actualización del anterior y no se pierden los datos.

## Production

Contra `https://chatmap.hotosm.org/`. Hay dos perfiles para la misma app:
`production` genera un `.aab` para Play Store y `production-apk` genera un
`.apk` para instalar directo.

### Antes del primer build de producción

- **Definir el `package` definitivo** en `app.json` (`android.package`). Hoy es
  `com.anonymous.chatmapapp`, un valor de plantilla. Una vez publicado en Play
  Store no se puede cambiar: cambiarlo crea otra app. Las variantes Dev y Local
  toman ese mismo valor con su sufijo.
- **Elegir un canal por usuario.** Play Store vuelve a firmar la app con su
  propia clave (Play App Signing). Por eso una app instalada desde Play Store no
  se puede actualizar con el APK directo, ni al revés. Para cambiar de canal hay
  que desinstalar, y se pierden los datos locales.

### Hacer una versión nueva

1. Subir `version` en `app.json`, por ejemplo de `1.0.0` a `1.1.0`. Es la
   versión que ve el usuario. El `versionCode` lo sube EAS en cada build.
2. Correr los chequeos de [Antes de cualquier build](#antes-de-cualquier-build).
3. Lanzar el build según el canal.

   Play Store:

   ```bash
   npx eas-cli@latest build --profile production --platform android
   npx eas-cli@latest submit --profile production --platform android --latest
   ```

   `submit` sube el último `.aab` a Play Console. Necesita una clave de cuenta
   de servicio de Google. La primera subida de la app a Play Console tiene que
   ser manual.

   APK directo:

   ```bash
   npx eas-cli@latest build --profile production-apk --platform android
   ```

   EAS muestra un link para descargar el `.apk`.

## Variables de entorno en EAS

| Entorno de EAS | Perfiles | `EXPO_PUBLIC_API_URL` |
|---|---|---|
| `development` | `local`, `development` | `https://dev.chatmap.hotosm.org/` |
| `production` | `production`, `production-apk` | `https://chatmap.hotosm.org/` |

El perfil `local` declara el entorno `development`, pero el dev client no lleva
el JavaScript adentro, así que esa URL no se usa: la app toma la de `.env.local`.

```bash
npx eas-cli@latest env:list --environment development
npx eas-cli@latest env:set --name EXPO_PUBLIC_API_URL --value <url> --environment development --visibility plaintext
```

Un cambio en una variable se aplica recién en el próximo build. Las variables
opcionales de detección de conexión (`EXPO_PUBLIC_HEALTH_*`, en `.env.example`)
se cargan de la misma forma si hace falta cambiarlas.

## Qué se sube a EAS

`.easignore`, en la raíz del repo, hace que EAS suba solo `chatmap-app/` y no el
monorepo entero. Ese archivo reemplaza a todos los `.gitignore` para EAS: una
regla nueva en `chatmap-app/.gitignore` también hay que copiarla ahí. Para ver
exactamente qué se sube:

```bash
npx eas-cli@latest build:inspect --platform android --profile development --stage archive --output /tmp/eas-archive
```

## Problemas comunes

- **La app se cierra apenas abre.** Falta `EXPO_PUBLIC_API_URL`. En Local,
  revisar `.env.local` y reiniciar Metro. En un build, revisar `env:list` del
  entorno del perfil.
- **En Local la app no llega al servidor.** Revisar que el backend esté
  corriendo y volver a correr `adb reverse tcp:8000 tcp:8000`.
- **Al escanear un QR de invitación con la cámara, Android pregunta con qué app
  abrirlo.** Las tres apps comparten el esquema `hot-chatmap://`. Hay que
  elegir la del servidor que generó la invitación. Escanear desde la propia app
  no tiene este problema.
