# Play Store Submission Checklist — SashaInfinity LMS

Code hardening + signing are DONE (see PLAY_STORE_RELEASE_PLAN.md). This is the
remaining human/console work to actually publish.

## A. Firebase — SHA fingerprints (Google Sign-In will break without these)

Upload-key SHA (add now):
```
SHA-1:   22:4E:64:2E:E8:0F:6C:DC:01:5D:76:B3:A4:6A:C0:71:FF:89:17:99
SHA-256: B3:17:EA:4F:81:92:4F:44:85:62:1A:01:65:EF:67:05:E6:24:CA:65:69:D5:C2:E5:4E:F4:EB:17:2E:E5:7A:44
```
- [ ] Firebase Console → Project Settings → Android app (com.sashainfinity.sasha_lms)
      → Add fingerprint → paste SHA-1 and SHA-256 → Save
- [ ] Re-download google-services.json, replace flutter_app/android/app/google-services.json
- [ ] AFTER first Play upload: copy Google's **App signing key** SHA-1 + SHA-256 from
      Play Console → Setup → App signing, add THOSE to Firebase too (store cert differs
      from upload cert — Google login fails on store installs without this)

## B. Store listing assets (Play Console → Main store listing)
- [ ] App icon 512×512 PNG (export from assets/icon/app_icon.png)
- [ ] Feature graphic 1024×500 PNG
- [ ] Phone screenshots ×2–8 (min 2), 1080×1920 or similar
- [ ] 7" + 10" tablet screenshots (optional but recommended)
- [ ] Short description (≤80 chars)
- [ ] Full description (≤4000 chars)
- [ ] App title: "Sasha Infinity" (matches manifest)
- [ ] Category: Education
- [ ] Contact email + website

## C. Privacy & compliance (Play Console → App content)
- [ ] Privacy policy URL (publicly hosted — required, app collects email/name/photo)
- [ ] Data safety form:
      - Personal: email, name, photos (Google profile)
      - App activity, device IDs (FCM token)
      - Financial: payment via Razorpay (declare Razorpay as processor)
      - Encryption in transit: Yes (HTTPS)
      - Data deletion mechanism: declare how users delete account/data
- [ ] Content rating questionnaire → Education
- [ ] Target audience + ads declaration (no ads = declare none)
- [ ] Government-app / financial-features declarations if prompted (payments)

## D. Deep links (App Links verification)
Manifest has autoVerify for https://sashainfinity.com/verify-email.
- [ ] Host https://sashainfinity.com/.well-known/assetlinks.json containing the
      **App signing key** SHA-256 (get from Play Console after first upload)
- [ ] Format: package com.sashainfinity.sasha_lms, sha256_cert_fingerprints = [App signing SHA-256]
- [ ] Custom scheme sashalms://verify-email works regardless (fallback, already fine)

## E. Upload & rollout (Play Console)
- [ ] Create app → set up Internal testing track
- [ ] Upload app-release.aab (build/app/outputs/bundle/release/)
- [ ] First upload auto-enrolls Play App Signing
- [ ] Review Pre-launch report (Google runs automated device tests) — fix crashes/warnings
- [ ] Add internal testers, verify install + Google login + Razorpay end-to-end on a
      store-delivered build (NOT your local APK — the signing cert differs)
- [ ] Promote Internal → Closed → Production
- [ ] Staged rollout (e.g. 20%) for first production release

## F. Per-release routine (every future update)
- [ ] Bump version in pubspec.yaml (e.g. 1.0.1+2 — versionCode must strictly increase)
- [ ] flutter build appbundle --release
- [ ] Upload new AAB, add release notes, roll out

## Keystore safety (do once, do NOT skip)
- [ ] Back up E:/keys/upload-keystore.jks in TWO safe places (cloud + offline)
- [ ] Store the keystore password in a password manager
- [ ] Losing the upload key → Play Console → request upload key reset (recoverable)
- [ ] key.properties stays git-ignored — never commit it
