# TV Reader Android TV Wrapper

This is a small Kotlin Android TV app that opens the web reader in a fullscreen
WebView. It defaults to:

```
https://reader.example.com/tv
```

## Build

This machine has the required CLI tooling installed with Homebrew:

- JDK 17: `/opt/homebrew/opt/openjdk@17`
- Android SDK command-line tools: `/opt/homebrew/share/android-commandlinetools`
- Gradle wrapper: `./gradlew`

Build from this directory with the helper script:

```
./build-tv.sh
```

The debug APK is written to:

```
app/build/outputs/apk/debug/app-debug.apk
```

## Local Server Override

For LAN testing, override the URL at build time:

```
./build-tv.sh :app:assembleDebug -PtvReaderUrl=http://192.168.1.50:8080/tv
```

Install a debug build to a connected Android TV device:

```
./build-tv.sh :app:installDebug -PtvReaderUrl=http://192.168.1.50:8080/tv
```

Debug builds allow cleartext HTTP so local LAN URLs work. Release builds should
use HTTPS, which matches the production `https://reader.example.com/tv` default.

Run lint:

```
./build-tv.sh :app:lintDebug
```

## Controls

- D-pad Right, Select, Enter, Space: next spread
- D-pad Left, Back, previous media key: previous spread
- If the page fails to load, Select retries.
