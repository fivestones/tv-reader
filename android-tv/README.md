# TV Reader Android TV Wrapper

This is a small Kotlin Android TV app that opens the web reader in a fullscreen
WebView. Set the default server in the repo `.env` file:

```
TV_READER_SERVER_URL=https://reader.example.com
```

The TV can also be pointed at a different server later from the in-app settings screen.

## Build

The project uses the checked-in Gradle wrapper plus JDK 17 and the Android SDK command-line tools.
`./build-tv.sh` defaults `JAVA_HOME` and `ANDROID_HOME` to the Homebrew paths used on this repo's primary macOS setup; override them in your shell if your toolchain lives elsewhere.

Build from this directory with the helper script:

```
./build-tv.sh
```

The debug APK is written to:

```
app/build/outputs/apk/debug/app-debug.apk
```

## Local Server Override

For LAN testing, override the server at build time:

```
./build-tv.sh :app:assembleDebug -PtvReaderServerUrl=http://192.168.1.50:8080
```

Install a debug build to a connected Android TV device:

```
./build-tv.sh :app:installDebug -PtvReaderServerUrl=http://192.168.1.50:8080
```

Debug builds allow cleartext HTTP so local LAN URLs work. Release builds should
use HTTPS.

Run lint:

```
./build-tv.sh :app:lintDebug
```

## Controls

- D-pad Right, Select, Enter, Space: next spread
- D-pad Left, previous media key: previous spread
- Back or Menu: settings
- If no server is configured, or if the main reader page fails to load, the app shows the native server picker overlay.
