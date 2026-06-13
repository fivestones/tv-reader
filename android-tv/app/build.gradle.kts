import java.io.File

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

fun String.asBuildConfigString(): String {
    return "\"" + replace("\\", "\\\\").replace("\"", "\\\"") + "\""
}

fun loadEnvFile(file: File): Map<String, String> {
    if (!file.exists()) {
        return emptyMap()
    }
    return file.readLines()
        .map { it.trim() }
        .filter { it.isNotEmpty() && !it.startsWith("#") && it.contains("=") }
        .associate {
            val key = it.substringBefore("=").trim()
            val value = it.substringAfter("=").trim().trim('"', '\'')
            key to value
        }
}

val repoEnv = loadEnvFile(rootProject.layout.projectDirectory.file("../.env").asFile)
val tvReaderServerUrl = providers.gradleProperty("tvReaderServerUrl")
    .orElse(providers.environmentVariable("TV_READER_SERVER_URL"))
    .orElse(repoEnv["TV_READER_SERVER_URL"] ?: repoEnv["TV_READER_URL"] ?: "")

android {
    namespace = "im.dat.tvreader"
    compileSdk = 35

    defaultConfig {
        applicationId = "im.dat.tvreader"
        minSdk = 23
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
        buildConfigField("String", "TV_READER_SERVER_URL", tvReaderServerUrl.get().asBuildConfigString())
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

}

kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
    }
}
