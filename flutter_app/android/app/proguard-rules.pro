# Flutter Wrapper
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.**  { *; }
-keep class io.flutter.util.**  { *; }
-keep class io.flutter.view.**  { *; }
-keep class io.flutter.**  { *; }
-keep class io.flutter.plugins.**  { *; }

# Dart
-keep class java.lang.reflect.Method { *; }
-keep class java.lang.reflect.Field { *; }
-keep class java.lang.Class { *; }
-keep class java.lang.reflect.Constructor { *; }

# General
-dontwarn android.support.**
-keep class android.support.** { *; }
-keep class androidx.** { *; }
-dontwarn androidx.**
-dontwarn com.google.android.gms.**
-keep class com.google.android.gms.** { *; }
-dontwarn com.google.android.play.core.**

# Firebase
-keep class com.google.firebase.** { *; }
-dontwarn com.google.firebase.**
-keep class com.google.android.gms.common.api.internal.** { *; }

# Network / Dio
-keep class okhttp3.** { *; }
-keep interface okhttp3.** { *; }
-dontwarn okhttp3.**
-dontwarn okio.**

# Model classes for JSON
-keep class * extends java.lang.Object {
  @com.google.gson.annotations.SerializedName <fields>;
}

# Flutter Secure Storage
-keep class com.it_nomads.fluttersecurestorage.** { *; }
-dontwarn com.it_nomads.fluttersecurestorage.**

# Razorpay — reflection-heavy SDK; R8 strips its classes and payment crashes
# only in release. Keep the SDK and its ProGuard annotation contract.
-keep class com.razorpay.** { *; }
-dontwarn com.razorpay.**
-keep class proguard.annotation.** { *; }
-dontwarn proguard.annotation.**
-keepclassmembers class * { @proguard.annotation.Keep *; }
-keepattributes *Annotation*
-optimizations !method/inlining/*
-keepclasseswithmembers class * {
  public void onPayment*(...);
}

# ktor (pulled transitively) references desktop-only java.lang.management.*
# classes that don't exist on Android — let R8 ignore them instead of aborting.
-dontwarn java.lang.management.ManagementFactory
-dontwarn java.lang.management.RuntimeMXBean
-dontwarn java.lang.management.**
-dontwarn io.ktor.**
