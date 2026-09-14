# Android Release Signing — Play App Signing (do once)

You keep an **upload key**. Google keeps the real **app signing key** (created on first
upload). If you ever lose the upload key, Play Console can reset it — you are never
permanently locked out. This is the recommended setup.

## Step 1 — Generate the upload keystore

Run in a terminal (NOT inside the repo). Pick strong passwords and record them in a
password manager — losing them means regenerating the upload key via Play Console.

```bash
keytool -genkey -v -keystore upload-keystore.jks \
  -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```

It asks for: keystore password, your name/org (any answers), then key password
(press Enter to reuse the keystore password).

Move the file somewhere safe outside the project, e.g.:
```
E:\keys\upload-keystore.jks
```

## Step 2 — Create android/key.properties

Create `flutter_app/android/key.properties` (already git-ignored — verify with
`git status` that it does NOT appear):

```properties
storePassword=YOUR_KEYSTORE_PASSWORD
keyPassword=YOUR_KEY_PASSWORD
keyAlias=upload
storeFile=E:/keys/upload-keystore.jks
```

Use forward slashes in `storeFile` even on Windows.

`build.gradle.kts` already reads this file and signs release with it when present —
no code change needed.

## Step 3 — Build the app bundle

```bash
cd flutter_app
flutter clean
flutter pub get
flutter build appbundle --release
# -> build/app/outputs/bundle/release/app-release.aab
```

## Step 4 — First upload enrolls Play App Signing

1. Play Console → create app → Internal testing → upload `app-release.aab`
2. Google auto-enrolls Play App Signing on first upload
3. Play Console → Setup → App signing shows two certs:
   - **App signing key certificate** (Google's — used by installed apps)
   - **Upload key certificate** (yours)

## Step 5 — Register BOTH SHA fingerprints with Firebase (critical)

Store builds are re-signed by Google, so their cert differs from your upload cert.
Google Sign-In breaks unless Firebase knows the **App signing key** SHA.

1. Play Console → App signing → copy **SHA-1** and **SHA-256** of the *App signing key*
2. Firebase Console → Project settings → your Android app → Add fingerprint → paste both
3. Re-download `google-services.json` if Firebase says to, replace the one in
   `flutter_app/android/app/`

Also grab the SHA of your **upload key** (for local release testing on-device):
```bash
keytool -list -v -keystore E:/keys/upload-keystore.jks -alias upload
```
Add that SHA to Firebase too, so a locally-built release APK can also do Google login.

## Recovery notes
- Back up `upload-keystore.jks` + passwords in 2 places.
- Lost upload key → Play Console → request upload key reset (Google re-issues).
- App signing key is Google-held → never at risk on your side.
