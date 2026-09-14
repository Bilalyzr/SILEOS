# Play Store Production Release Plan — SashaInfinity LMS (Android)

Scope: Android / Google Play only. Signing: **Play App Signing** (Google holds the app
signing key; you keep an upload key). Cert pinning: deferred to a later update.

Work is ordered so each phase is independently verifiable. Nothing here touches the
auth/login flow.

---

## Phase 0 — Baseline (verify current state)

- [ ] `flutter --version` recorded, `flutter doctor` clean
- [ ] `flutter pub get` succeeds
- [ ] Current debug build installs and Google login works (already confirmed)

---

## Phase 1 — BLOCKERS (app will be rejected or crash without these)

### 1.1 Upload keystore + Play App Signing
**Why:** Play Store rejects debug-signed AABs. With Play App Signing, Google manages the
real signing key; you only generate and guard an *upload* key.

Idea / steps (passwords stay on your machine — never commit them):

```bash
# Generate the upload keystore (run once, keep the .jks safe + backed up)
keytool -genkey -v -keystore upload-keystore.jks \
  -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```

Place `upload-keystore.jks` OUTSIDE the repo (e.g. `E:\keys\`), then create
`flutter_app/android/key.properties` (already git-ignored):

```properties
storePassword=<password you chose>
keyPassword=<password you chose>
keyAlias=upload
storeFile=E:/keys/upload-keystore.jks
```

- [ ] Keystore generated, stored outside repo, backed up (losing it = can't update app)
- [ ] `key.properties` created and confirmed git-ignored (`git status` shows nothing)
- [ ] `build.gradle.kts` already reads `key.properties` — no code change needed
- [ ] First Play Console upload enrolls into Play App Signing automatically

### 1.2 Remove app-wide cleartext traffic
**Why:** `usesCleartextTraffic="true"` in the manifest overrides the good
`network_security_config.xml` and re-enables HTTP (MITM risk).

- [ ] Delete `android:usesCleartextTraffic="true"` from `AndroidManifest.xml` (line 21)
- [ ] Localhost dev still works — debug/profile res overlays already permit cleartext
- [ ] Verify release build reaches `https://sashainfinity.com` fine

### 1.3 Razorpay ProGuard/R8 keep rules
**Why:** `isMinifyEnabled = true` strips Razorpay reflection classes → payment screen
crashes only in release (not debug).

- [ ] Add to `proguard-rules.pro`:
```pro
# Razorpay
-keep class com.razorpay.** { *; }
-dontwarn com.razorpay.**
-keep class proguard.annotation.** { *; }
-dontwarn proguard.annotation.**
-keepclassmembers class * { @proguard.annotation.Keep *; }
```
- [ ] Also confirm other reflection-heavy SDKs survive R8: image_cropper (uCrop),
      bunny player, google_sign_in (rules already present for Firebase/GMS)

### 1.4 Version bump discipline
**Why:** Every Play upload needs a strictly higher `versionCode`.

- [ ] Set `version:` in `pubspec.yaml` to `1.0.0+1` for first release; bump `+N` each upload
- [ ] Document the bump step in release checklist (Phase 5)

---

## Phase 2 — Log / data hygiene (privacy + Play data-safety)

### 2.1 Strip debug prints that leak PII in release
**Why:** `print()` writes to logcat in release too. Current leaks: auth state (user email)
and Firebase/reset flows.

- [ ] Remove `print('[Router redirect] ...')` from `routes.dart:52` (was a debug aid)
- [ ] Gate or remove `print(...)` in `auth_repository_impl.dart` (lines ~253–337) —
      wrap in `if (kDebugMode)` or route through a logger that no-ops in release
- [ ] Sweep remaining `print(`/`debugPrint(` (29 across 11 files) — keep only
      `kDebugMode`-gated ones
- [ ] Confirm `LogInterceptor` stays off in prod (already gated by `AppConfig.enableLogs`)

### 2.2 Play Console Data Safety form (no code, but required to publish)
- [ ] Declare collected data: email, name, profile photo (Google), FCM token, payment
      (via Razorpay), images (profile)
- [ ] Link privacy policy URL (must be publicly hosted)
- [ ] Declare encryption in transit (HTTPS) ✓

---

## Phase 3 — Store assets & metadata (no code)

- [ ] App icon 512×512 (have `assets/icon/app_icon.png` — export at 512)
- [ ] Feature graphic 1024×500
- [ ] Screenshots: min 2 phone (recommend 4–8), 7"/10" tablet optional
- [ ] Short description (80 chars) + full description (4000 chars)
- [ ] Content rating questionnaire
- [ ] Category (Education), contact email, privacy policy URL
- [ ] App title "Sasha Infinity" (matches manifest label ✓)

---

## Phase 4 — Deep links & Firebase (functional correctness in prod)

### 4.1 App Links verification
**Why:** manifest has `autoVerify="true"` for `https://sashainfinity.com/verify-email`.
Without hosted `assetlinks.json`, HTTPS deep links silently fall back to browser.

- [ ] Host `https://sashainfinity.com/.well-known/assetlinks.json` with the app's
      SHA-256 cert fingerprint (get it from Play Console → App Signing after upload)
- [ ] Custom-scheme `sashalms://verify-email` works regardless (fallback ✓)
- [ ] Test cold-start email verify link opens the app

### 4.2 Firebase release config
- [ ] `google-services.json` present ✓ — confirm it's the **production** Firebase project
- [ ] Add the Play App Signing SHA-1 + SHA-256 to Firebase console (else Google
      Sign-In breaks for store builds — the store cert differs from your upload cert)
- [ ] Crashlytics receiving events from a release build
- [ ] Verify push (FCM) works on a release build

---

## Phase 5 — Build, test, ship

### 5.1 Release build
```bash
cd flutter_app
flutter clean
flutter pub get
flutter build appbundle --release
# output: build/app/outputs/bundle/release/app-release.aab
```
- [ ] Build succeeds with R8 minify on
- [ ] `flutter analyze` clean (no errors)

### 5.2 Real-device release smoke test (install the AAB via bundletool or internal testing)
- [ ] Google login end-to-end
- [ ] Email register + verify link
- [ ] Course list / video playback (YouTube + Bunny paths)
- [ ] **Razorpay checkout completes** (the R8 crash surfaces here)
- [ ] Profile photo pick + crop + upload
- [ ] Push notification received
- [ ] No PII in logcat (`adb logcat | grep -i email`)

### 5.3 Play Console rollout
- [ ] Create app, upload AAB to **Internal testing** track first
- [ ] Fix any pre-launch report warnings (Google runs automated device tests)
- [ ] Promote to Closed → Open/Production after internal pass
- [ ] Staged rollout (e.g. 20%) for first production release

---

## Priority order to execute
1. **1.3 Razorpay ProGuard** (silent release crash — highest risk)
2. **1.2 cleartext removal** + **2.1 print hygiene** (security/privacy, quick)
3. **1.1 keystore / Play App Signing** (needs your passwords)
4. **4.2 Firebase SHA + 4.1 assetlinks** (Google login + deep links in prod)
5. Build → internal test → rollout

## Deferred (post-v1)
- Certificate pinning (config has a ready TODO with the openssl command)
- iOS / App Store
- Automated CI/CD signing
