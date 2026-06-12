# TV Reader Android TV Wrapper

This is a small Kotlin Android TV app that opens the web reader in a fullscreen
WebView. It defaults to:

```
https://reader.example.com/tv
```

## Build

Open this `android-tv/` directory in Android Studio, or build from this
directory with Gradle if your machine has Android Gradle tooling installed:

```
gradle :app:assembleDebug
```

Install a debug build to a connected Android TV device:

```
gradle :app:installDebug
```

## Local Server Override

For LAN testing, override the URL at build time:

```
gradle :app:installDebug -PtvReaderUrl=http://192.168.1.50:8080/tv
```

Debug builds allow cleartext HTTP so local LAN URLs work. Release builds should
use HTTPS, which matches the production `https://reader.example.com/tv` default.

## Controls

- D-pad Right, Select, Enter, Space: next spread
- D-pad Left, Back, previous media key: previous spread
- If the page fails to load, Select retries.
