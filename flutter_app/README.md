# SashaInfinity LMS Flutter App

Mobile application for SashaInfinity Learning Management System.

## Tech Stack

- **Framework**: Flutter 3.x
- **State Management**: Riverpod (flutter_riverpod)
- **Routing**: go_router
- **Networking**: Dio + Retrofit
- **Local Storage**: Hive + flutter_secure_storage
- **Video**: video_player, chewie, youtube_player_flutter
- **Payments**: razorpay_flutter
- **Firebase**: Core, Crashlytics, Analytics, Messaging

## Project Structure

```
lib/
├── config/                 # App configuration
├── core/                   # Core functionality
│   ├── constants/         # App constants
│   ├── errors/            # Error handling
│   ├── network/           # Network layer
│   ├── storage/           # Local storage
│   └── utils/             # Utilities
├── features/              # Feature modules
│   ├── auth/             # Authentication
│   ├── courses/          # Courses
│   ├── lessons/          # Lessons
│   ├── quizzes/          # Quizzes
│   ├── payments/         # Payments
│   └── profile/          # User profile
├── shared/               # Shared widgets and providers
│   ├── widgets/         # Reusable widgets
│   └── providers/       # Shared providers
└── l10n/                # Internationalization
```

## Getting Started

### Prerequisites

- Flutter SDK 3.x
- Dart 3.x
- Android Studio / Xcode (for mobile development)

### Installation

1. Install dependencies:
   ```bash
   flutter pub get
   ```

2. Run the app:
   ```bash
   flutter run
   ```

### Environment Configuration

Environment variables will be configured in `lib/config/env.dart` (to be created).

## Architecture

This app follows Clean Architecture principles with clear separation of concerns:

- **Data Layer**: Models, repositories, data sources
- **Domain Layer**: Entities, use cases, repository interfaces
- **Presentation Layer**: Pages, widgets, providers

## Contributing

This is part of the SashaInfinity LMS project. Please follow the established coding standards and patterns.
