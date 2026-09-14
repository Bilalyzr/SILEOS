# SashaInfinity LMS — Play Store Asset Brief

Everything below is pulled from the live Flutter codebase (`flutter_app/`), not guessed.

App: **Sasha Infinity** · Package: `com.sashainfinity.sasha_lms` · Tagline: *Democratize Education*

---

## 1. Brand colors

### Core brand
| Role | Hex | Notes |
|------|-----|-------|
| **Primary** | `#F97316` | Orange-500 — the brand orange (infinity mark, CTAs) |
| **Primary dark** | `#EA580C` | Orange-600 — pressed/gradient end |
| **Secondary** | `#0C4A6E` | Dark blue |

### Semantic
| Role | Hex |
|------|-----|
| Success | `#22C55E` |
| Warning | `#EAB308` |
| Danger | `#EF4444` |
| Info | `#0EA5E9` |

### Surfaces — light theme
| Role | Hex |
|------|-----|
| Background | `#FFFFFF` |
| Surface / card | `#F8FAFC` (Slate-50) |
| Text | `#0F172A` (Slate-900) |
| Muted text | `#64748B` (Slate-500) |
| Border (hairline) | `#E9EDF2` |
| Input fill | `#F1F5F9` (Slate-100) |

### Surfaces — dark theme
| Role | Hex |
|------|-----|
| Background | `#0B1118` (near Slate-950) |
| Surface / card | `#161E2A` |
| Text | `#F8FAFC` (Slate-50) |
| Muted text | `#94A3B8` (Slate-400) |
| Border (hairline) | `#24303F` |
| Input fill | `#1E293B` (Slate-800) |

Source: `lib/config/theme.dart`

---

## 2. Typography

Both via the `google_fonts` package (`^6.3.2`) — no bundled font files.

| Font | Used for | Frequency in code |
|------|----------|-------------------|
| **Inter** | Body text, buttons, inputs, labels — the workhorse | ~140 usages |
| **Plus Jakarta Sans** | Headings, app-bar titles — display/heading face | ~125 usages |

Designers: use **Plus Jakarta Sans** for headlines, **Inter** for body/supporting text. Both free on Google Fonts.

---

## 3. Logo assets

| File | Size | Format | Notes |
|------|------|--------|-------|
| `assets/images/sasha-logo.png` | 1563×1563 | PNG (palette) | Full logo lockup |
| `assets/icon/app_icon.png` | 1024×1024 | PNG RGBA | Source app icon |
| `assets/icon/app_icon_foreground.png` | 1024×1024 | PNG RGBA | Adaptive-icon foreground layer (also used as splash image) |
| `assets/icons/google_logo.svg` | vector | SVG | Third-party (Google Sign-In button) |

**Brand mark description** (from the official logo): geometric **orange gradient infinity (∞)** drawn as a rounded block with two white lens-shaped cutouts; **"SASHA"** wordmark in wide-tracked uppercase with a **teal gradient**; **"Democratize Education"** tagline in a **light-blue handwritten script**; teal half-circle accents flanking the mark.

---

## 4. Key screens to showcase (screenshot shortlist)

Ranked by visual distinctiveness / marketing value.

| # | Screen | Route | Source file | Why it sells |
|---|--------|-------|-------------|--------------|
| 1 | **AR Gallery** | in-app (Home) | `lib/features/ar_gallery/presentation/pages/ar_gallery_page.dart` | **The differentiator** — 100+ interactive 3D math models (Möbius strip, Klein bottle, Hilbert curve). Nothing else looks like this. |
| 2 | **Home / feed** | `/` | `lib/features/home/presentation/pages/home_page.dart` | Brand-forward: 3D Sasha character, feature cards, "100+ AR Models" stat tiles |
| 3 | **Course detail + video player** | `/courses/:id` | `lib/features/courses/presentation/pages/course_detail_page.dart` | Core product — video lessons, curriculum, pricing |
| 4 | **Dashboard / progress** | `/` tab 2 | `lib/features/dashboard/presentation/pages/dashboard_page.dart` | Progress tracking, enrolled courses |
| 5 | **Quiz** | `/courses/:courseId/quizzes/:quizId` | `lib/features/quizzes/presentation/pages/quiz_taking_page.dart` | Interactive learning proof |
| 6 | **Certificate** | in-app | `lib/features/certificates/` | Outcome/credibility shot |
| 7 | **Get Started / Login** | `/get-started` | `lib/features/auth/presentation/pages/get_started_page.dart` | 3D Sasha character hero — strong brand first impression |

Main bottom nav: **Home · Catalog · Dashboard · Profile** (`main_scaffold.dart`)

---

## 5. App icon (Android build)

**Source of truth:** `assets/icon/app_icon.png` (1024×1024) — configured via `flutter_launcher_icons`.

Generated launcher icons in the build:
```
android/app/src/main/res/mipmap-{mdpi,hdpi,xhdpi,xxhdpi,xxxhdpi}/ic_launcher.png
android/app/src/main/res/drawable-{mdpi..xxxhdpi}/ic_launcher_foreground.png
android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml   (adaptive)
```

Adaptive icon config (`pubspec.yaml`):
- foreground: `assets/icon/app_icon_foreground.png`
- background: `#FFFFFF`
- iOS: alpha removed, background `#FFFFFF`

**Play Store 512×512 icon: already exported → `store_assets/play_icon_512.png`** (derived from the real app icon, so store and device icons match).

---

## 6. Existing marketing / brand assets in-project

| Asset | Where | Use for feature graphic |
|-------|-------|------------------------|
| **Native splash screen** | `flutter_native_splash` config | White `#FFFFFF` background + `app_icon_foreground.png` centred. Establishes the light/white brand surface. |
| **3D Sasha character** | `assets/models/Sasha-Character.glb` | The mascot shown on Get Started + login. Orange/teal robot-like figure — usable as a hero element. |
| **AR model thumbnails** | `assets/models/ar_thumbnails/*.webp` | ~40+ rendered 3D math models. Great texture/background material for banners. |
| **Web AR models** | `frontend/public/models/ar/*.glb` | Full 3D model library (Möbius, Klein bottle, gyroid, Penrose triangle…) |
| **App icon** | `assets/icon/app_icon.png` | The infinity mark itself |

---

## Play Store asset requirements (spec)

| Asset | Spec | Status |
|-------|------|--------|
| App icon | 512×512 PNG/JPEG, ≤1 MB | ✅ `store_assets/play_icon_512.png` |
| Feature graphic | **1024×500** PNG/JPEG, ≤15 MB | ⏳ in design |
| Phone screenshots | 2–8, PNG/JPEG, ≤8 MB each, 16:9 or 9:16, 320–3840 px/side. **4+ at ≥1080 px for promo eligibility** | ⏳ capture from device (1080×2340) |
| 7" tablet screenshots | up to 8, same ratio rules | ⏳ |
| 10" tablet screenshots | up to 8, 1080–7680 px/side | ⏳ |

---

## Store listing copy (drafted from actual app features)

**Short description (77/80):**
> Learn coding, AI & data science with video courses, AR models and an AI tutor.

**Full description:** see the drafted long-form copy — covers courses (Full Stack with AI, Data Analytics/Excel, React JS, Tamil + English), AR gallery (100+ 3D models), quizzes/assignments, certificates, internships, Razorpay checkout with coupons.
