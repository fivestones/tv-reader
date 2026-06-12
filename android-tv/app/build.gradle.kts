plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

fun String.asBuildConfigString(): String {
    return "\"" + replace("\\", "\\\\").replace("\"", "\\\"") + "\""
}

val tvReaderUrl = providers.gradleProperty("tvReaderUrl").orElse("https://reader.example.com/tv")

android {
    namespace = "im.dat.tvreader"
    compileSdk = 35

    defaultConfig {
        applicationId = "im.dat.tvreader"
        minSdk = 23
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
        buildConfigField("String", "TV_READER_URL", tvReaderUrl.get().asBuildConfigString())
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}
