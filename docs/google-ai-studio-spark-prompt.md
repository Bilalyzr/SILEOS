# SashaInfinity LMS Mobile App - Complete Prompt for Google AI Studio Spark

Copy this entire prompt and paste into Google AI Studio Spark (aistudio.google.com) to generate the complete Flutter app.

---

# SashaInfinity LMS Flutter Mobile App

## Overview
Build a complete Learning Management System mobile app for SashaInfinity LMS. This is a production app that will replace the existing React web frontend. The web version is live at: https://lms.sashainfinity.com - use this as UI/UX reference.

## Tech Stack (Required)
- Flutter 3.x (Dart)
- Riverpod 2.x (state management with code generation)
- GoRouter 13.x (navigation/routing)
- Dio 5.x (HTTP client)
- Hive + FlutterSecureStorage (local persistence)
- Chewie + youtube_player_flutter (video playback)
- Razorpay_flutter (payment integration)
- Cached_network_image (image caching)
- Shimmer (loading placeholders)
- Freezed (immutable classes)

## API Integration
Base URL: https://backend.sashainfinity.com/api/v1
All requests use Bearer token authentication
Tokens expire after 30 minutes - implement auto-refresh on 401

### Complete API Endpoints

#### Authentication (/api/v1/auth)
```
POST /login
Request: { "email": "user@example.com", "password": "password123" }
Response: {
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 123,
    "user_email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "student",
    "avatar_url": "https://...",
    "is_verified": true
  }
}

POST /register
Request: {
  "email": "user@example.com",
  "password": "password123",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+919876543210"
}
Response: { "user": {...}, "message": "Registration successful" }

POST /logout
Headers: Authorization: Bearer {token}
Response: { "message": "Logged out successfully" }

POST /refresh
Request: { "refresh_token": "..." }
Response: { "access_token": "...", "refresh_token": "..." }

GET /me
Headers: Authorization: Bearer {token}
Response: { "user": {...} }

POST /forgot-password
Request: { "email": "user@example.com" }
Response: { "message": "Password reset email sent" }

POST /reset-password
Request: { "token": "...", "new_password": "..." }
Response: { "message": "Password reset successful" }
```

#### Courses (/api/v1/courses)
```
GET /courses?page=1&page_size=20&category=tech&level=beginner&search=python&price_type=free
Response: {
  "courses": [
    {
      "id": 456,
      "post_title": "Complete Python Development",
      "post_content": "Course description...",
      "post_excerpt": "Short description",
      "course_thumbnail": "https://...",
      "course_price": 4999,
      "course_sale_price": 2999,
      "course_price_type": "paid",
      "course_category": "meiporul",
      "course_level": "beginner",
      "course_duration": 120,
      "total_lessons": 45,
      "total_quizzes": 5,
      "rating": 4.5,
      "enrollment_count": 1250,
      "post_author": {
        "id": 789,
        "first_name": "Jane",
        "last_name": "Instructor",
        "avatar_url": "https://..."
      },
      "slug": "complete-python",
      "is_enrolled": false
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20
}

GET /courses/{id} or /courses/{slug}
Response: {
  "id": 456,
  "post_title": "Complete Python Development",
  "post_content": "Full description with HTML",
  "course_thumbnail": "https://...",
  "course_price": 4999,
  "course_sale_price": 2999,
  "course_price_type": "paid",
  "course_level": "beginner",
  "course_duration": 120,
  "total_lessons": 45,
  "lessons": [
    {
      "id": 1001,
      "post_title": "Introduction to Python",
      "lesson_content": "Content here...",
      "lesson_video_url": "https://youtube.com/watch?v=...",
      "lesson_duration": 600,
      "lesson_order": 1,
      "is_preview": true,
      "is_completed": false
    }
  ],
  "quizzes": [
    {
      "id": 201,
      "post_title": "Python Basics Quiz",
      "quiz_time_limit": 1800,
      "quiz_passing_grade": 70
    }
  ],
  "post_author": {...},
  "rating": 4.5,
  "review_count": 125,
  "enrollment_count": 1250,
  "what_you_will_learn": ["Python basics", "OOP", "Projects"],
  "requirements": ["No prior experience"],
  "is_enrolled": false,
  "progress": 0
}

POST /enrollments
Request: { "course_id": 456 }
Response: { "message": "Enrolled successfully", "enrollment_id": 789 }

GET /enrollments/my-courses
Response: {
  "enrollments": [
    {
      "id": 789,
      "course_id": 456,
      "enrolled_at": "2024-01-15T10:30:00Z",
      "progress": 35,
      "course": {...},
      "last_accessed_lesson": {...}
    }
  ]
}
```

#### Lessons (/api/v1/lessons)
```
GET /lessons/{id}
Response: {
  "id": 1001,
  "post_title": "Introduction to Python",
  "post_content": "Lesson content",
  "lesson_video_url": "https://youtube.com/watch?v=...",
  "lesson_video_type": "youtube",
  "lesson_duration": 600,
  "resources": [
    { "title": "Source Code", "url": "https://..." }
  ]
}
```

#### Progress (/api/v1/progress)
```
POST /progress/save
Request: {
  "lesson_id": 1001,
  "course_id": 456,
  "watched_seconds": 540,
  "total_seconds": 600
}
Response: { "message": "Progress saved", "completion_percentage": 90 }

POST /courses/{course_id}/lessons/{lesson_id}/complete
Response: { "message": "Lesson marked as complete" }
```

#### Quizzes (/api/v1/quizzes)
```
GET /quizzes/{quiz_id}
Response: {
  "id": 201,
  "post_title": "Python Basics Quiz",
  "post_content": "Test your knowledge",
  "quiz_time_limit": 1800,
  "quiz_passing_grade": 70,
  "quiz_max_attempts_allowed": 3,
  "attempts_remaining": 2,
  "questions": [
    {
      "id": 3001,
      "question_text": "What is Python?",
      "question_type": "multiple_choice",
      "answers": [
        { "id": 1, "answer_text": "A snake", "is_correct": false },
        { "id": 2, "answer_text": "A programming language", "is_correct": true }
      ],
      "explanation": "Python is a high-level programming language"
    }
  ]
}

POST /quizzes/{quiz_id}/submit
Request: {
  "quiz_id": 201,
  "answers": {
    "3001": 2,
    "3002": 1
  }
}
Response: {
  "attempt_id": 501,
  "score": 80,
  "total_score": 100,
  "passed": true,
  "percentage": 80,
  "answers_correct": 4,
  "total_questions": 5
}

GET /quizzes/{quiz_id}/attempts
Response: {
  "attempts": [
    {
      "id": 501,
      "score": 80,
      "passed": true,
      "completed_at": "2024-01-15T11:30:00Z"
    }
  ]
}
```

#### Payments (/api/v1/payments)
```
POST /payments/create-order
Request: { "course_id": 456, "amount": 2999 }
Response: {
  "order_id": "order_abc123",
  "amount": 299900,
  "currency": "INR",
  "razorpay_order_id": "rzp_..."
}

POST /payments/verify
Request: {
  "order_id": "order_abc123",
  "razorpay_payment_id": "pay_...",
  "razorpay_signature": "..."
}
Response: { "verified": true, "enrollment_id": 789 }
```

#### User Profile (/api/v1/users)
```
GET /users/me
Response: {
  "id": 123,
  "user_email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "student",
  "avatar_url": "https://...",
  "phone": "+919876543210",
  "bio": "Learning enthusiast"
}

PUT /users/me
Request: {
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+919876543210",
  "bio": "Updated bio"
}
Response: { "user": {...} }
```

#### Uploads (/api/v1/upload)
```
POST /upload/image
FormData: file (image), context (avatar)
Response: {
  "file_url": "/uploads/avatars/abc123.jpg",
  "filename": "abc123.jpg"
}
```

#### Company Portal (/api/v1)
```
GET /internships
Response: {
  "internships": [
    {
      "id": 1,
      "title": "Full Stack Developer Internship",
      "company": "Tech Corp",
      "location": "Chennai",
      "stipend": 10000,
      "duration": "3 months",
      "status": "applied"
    }
  ]
}

POST /work-logs
Request: {
  "date": "2024-01-15",
  "hours_worked": 8,
  "tasks_completed": "Built login page",
  "challenges_faced": "None"
}
Response: { "id": 456, "status": "pending" }

GET /work-logs?start_date=2024-01-01&end_date=2024-01-31
Response: { "work_logs": [...], "total_hours": 160 }
```

## UI/UX Specifications

### Design Reference
Website: https://lms.sashainfinity.com
Use this as visual reference for layouts, colors, components

### Color Palette
- Primary: #6750A4 (Purple)
- Secondary: #625B71
- Success: #4CAF50 (Green)
- Warning: #FF9800 (Orange)
- Danger: #F44336 (Red)
- Background: #FAFAFA
- Surface: #FFFFFF

### Typography
- Headline Large: 32sp, Bold
- Headline Medium: 24sp, Bold
- Headline Small: 20sp, Bold
- Body Large: 16sp, Regular
- Body Medium: 14sp, Regular
- Body Small: 12sp, Regular

### Screens & Components

#### 1. Splash Screen
- Centered logo and app name "SashaInfinity LMS"
- Loading spinner
- Gradient background (primary to secondary)
- Check authentication status
- Navigate to home or login

#### 2. Login Screen
- Logo at top
- Email input (with validation)
- Password input (with visibility toggle)
- "Forgot Password?" link
- "Sign In" button (full width)
- "Don't have an account? Register" link
- Show loading state on button during API call
- Error snackbar for failed login
- Remember email option

#### 3. Register Screen
- First Name and Last Name (side by side)
- Email input
- Phone (optional)
- Password input (min 6 chars)
- Confirm Password input
- "Create Account" button
- "Already have an account? Sign In" link
- Form validation before submission

#### 4. Home Screen (Bottom Nav: Home)
- Featured courses carousel (horizontal scroll)
- Categories pills (horizontal scroll): Meiporul, Seyappaduporul, Utporul, Tech, Business
- Popular courses section
- Continue Learning section (if enrolled)
- Search bar at top
- Shimmer loading placeholders

#### 5. Course Card Component
```dart
CourseCard(
  thumbnail: "https://...",
  title: "Complete Python Development",
  instructor: "Jane Instructor",
  instructorAvatar: "https://...",
  price: 2999,
  salePrice: 1999,
  isPaid: true,
  rating: 4.5,
  reviewCount: 125,
  duration: "10 hours",
  level: "beginner", // badge color
  enrollmentCount: 1250,
  isEnrolled: false,
  progress: 35, // if enrolled
  onTap: () => navigateToDetail()
)
```

#### 6. Course Listing Screen (Bottom Nav: Courses)
- Search bar with filter icon
- Filter chips: All, Free, Paid, Beginner, Intermediate, Advanced
- Course grid (2 columns on tablet, 1 on phone)
- Pull to refresh
- Load more on scroll (pagination)
- Empty state: "No courses found"
- Error state with retry button

#### 7. Course Detail Screen
- App bar with share button
- Course thumbnail (16:9 aspect ratio)
- Title, instructor info with avatar
- Stats row: Rating (star icon), Duration (clock icon), Students (user icon)
- Price display: Strike through original, show sale price
- Tabs: Overview, Curriculum, Reviews
- Tab 1 (Overview): Description, What you'll learn, Requirements
- Tab 2 (Curriculum): Accordion list of lessons with expand/collapse
  - Show lesson number, title, duration
  - Lock icon for non-enrolled (except preview lessons)
  - Checkmark for completed lessons
- Tab 3 (Reviews): Student reviews list
- Floating "Enroll Now" button (bottom)

#### 8. Lesson/Video Player Screen
- Full-screen video player at top (16:9)
- Video controls:
  - Play/Pause
  - Seek bar
  - Volume
  - Fullscreen toggle
  - Playback speed (0.5x, 1x, 1.5x, 2x)
- Below video: Lesson title, description
- "Mark as Complete" button (if not completed)
- "Download Resources" button (if available)
- Previous/Next lesson buttons
- Progress indicator: "Lesson 5 of 45"
- Auto-play next lesson when current completes
- Save progress every 10 seconds
- Rotate to landscape for fullscreen video

#### 9. Quiz Listing Screen
- List of quizzes for enrolled courses
- Each quiz card shows:
  - Quiz title
  - Course name
  - Duration (clock icon)
  - Passing score
  - Attempts remaining
  - "Start" or "Retake" button
- Badge for "Completed" or "Passed"

#### 10. Quiz Taking Screen
- Timer display at top (if time limit)
- Progress: "Question 5 of 20"
- Question card with:
  - Question number
  - Question text
  - Multiple choice options (radio buttons)
  - True/False buttons (for boolean type)
  - Text input (for fill-in-blank type)
- Navigation buttons: Previous, Next
- "Submit Quiz" button on last question
- Confirmation dialog before submit
- Disable changing answers after submit
- Auto-submit when timer expires

#### 11. Quiz Result Screen
- Circular progress indicator showing score percentage
- "Passed!" (green) or "Not Passed" (red) message
- Score: "80/100 points"
- Time taken: "Completed in 15 minutes"
- Review section:
  - List of all questions
  - Show user answer and correct answer
  - Green checkmark for correct
  - Red X for incorrect
  - Explanation for each question
- "Retake Quiz" button (if attempts remaining)
- "Back to Course" button

#### 12. Payment Screen
- Course summary card with thumbnail
- Course title
- Price breakdown:
  - Original price (strike through)
  - Discount (if any)
  - Final price
- Razorpay payment options:
  - UPI (Google Pay, PhonePe)
  - Cards (Visa, Mastercard)
  - Net Banking
  - Wallets (Paytm, Amazon Pay)
- "Pay Now" button
- Show processing state
- Success animation on payment complete
- Error dialog on payment failure

#### 13. Profile Screen (Bottom Nav: Profile)
- User avatar with edit overlay
- Name, email
- Stats cards (row):
  - Courses enrolled
  - Completed
  - Certificates
- Menu items:
  - My Courses
  - Certificates
  - Payment History
  - Wishlist
  - Settings
  - Help & Support
  - Logout
- Avatar upload: Choose from gallery or camera

#### 14. Settings Screen
- Language toggle: English / Tamil (தமிழ்)
- Theme toggle: Light / Dark / System
- Notifications toggle
- Clear cache button
- App version info

#### 15. Company Portal Screens
**Internships List:**
- Internship cards with company logo
- Position title, location (remote/on-site)
- Stipend amount
- Duration
- "Apply" button
- Filter tabs: Applied, In Progress, Completed

**Work Log Submission:**
- Date picker
- Hours worked input (number field)
- Tasks completed (multi-line text)
- Challenges faced (multi-line text)
- Attachments (optional)
- "Submit" button

**Work Log History:**
- Calendar view showing work days
- List of submitted logs
- Status badges: Pending (yellow), Approved (green), Rejected (red)
- Manager comment for rejected logs
- Weekly hours summary

#### 16. Bottom Navigation
- 4 tabs: Home, Courses, Quizzes, Profile
- Active tab highlighted with primary color
- Icons: home, book-open, clipboard-list, user
- Label below each icon

## Data Models

### User
```dart
class User {
  final int id;
  final String email;
  final String firstName;
  final String lastName;
  final String role; // student, instructor, admin, company, company_manager
  final String? avatarUrl;
  final String? phone;
  final String? bio;
  final bool isVerified;
  final DateTime? createdAt;
}
```

### Course
```dart
class Course {
  final int id;
  final String slug;
  final String title;
  final String description;
  final String excerpt;
  final String thumbnail;
  final double price;
  final double salePrice;
  final String priceType; // free, paid
  final String category; // meiporul, seyappaduporul, utporul, tech
  final String level; // beginner, intermediate, advanced
  final int duration; // in minutes
  final int totalLessons;
  final int totalQuizzes;
  final double rating;
  final int enrollmentCount;
  final User instructor;
  final bool isEnrolled;
  final int progress; // 0-100
  final List<String> whatYouWillLearn;
  final List<String> requirements;
  final List<Lesson> lessons;
  final List<Quiz> quizzes;
}
```

### Lesson
```dart
class Lesson {
  final int id;
  final String title;
  final String content;
  final String videoUrl;
  final String videoType; // youtube, bunny, direct
  final int duration; // in seconds
  final int order;
  final bool isPreview;
  final bool isCompleted;
  final List<Resource> resources;
}
```

### Quiz
```dart
class Quiz {
  final int id;
  final String title;
  final String description;
  final int timeLimit; // in seconds
  final int passingGrade; // percentage
  final int maxAttempts;
  final int attemptsRemaining;
  final List<Question> questions;
  final List<QuizAttempt> attempts;
}
```

### Question
```dart
class Question {
  final int id;
  final String text;
  final String type; // multiple_choice, true_false, fill_blank
  final List<Answer> answers;
  final String? explanation;
}
```

## Features & Requirements

### Authentication
- Token-based authentication with access and refresh tokens
- Auto-refresh access token before expiry
- Store tokens securely using flutter_secure_storage
- Clear tokens on logout
- Remember email option using shared_preferences

### Video Player
- Support YouTube videos using youtube_player_flutter
- Support direct MP4 using video_player + chewie
- Support Bunny.net CDN videos
- Detect video type from URL automatically
- Custom controls with:
  - Play/Pause
  - Seek bar with time display
  - Volume slider
  - Fullscreen toggle
  - Playback speed selector (0.5x, 0.75x, 1x, 1.25x, 1.5x, 2x)
- Auto-play next lesson
- Remember playback position
- Save progress to API

### Progress Tracking
- Save video progress every 10 seconds
- Mark lesson as complete when 90% watched
- Update course progress percentage
- Sync progress with API
- Show progress on course cards

### Quiz System
- Timer countdown (if time limit set)
- Auto-submit when timer expires
- Validate answers before submission
- Show results immediately after submission
- Review answers with explanations
- Track attempts remaining
- Prevent re-taking if no attempts left

### Payment Integration
- Razorpay integration
- Create order via API
- Open Razorpay checkout
- Handle payment success, failure, cancellation
- Verify payment via API
- Auto-enroll after successful payment

### Caching
- Cache course list using Hive
- Cache course details
- Cache lesson content for offline viewing
- Invalidate cache on pull-to-refresh
- Show cached data when offline
- Sync when connection restored

### Localization
- Support English and Tamil
- Store language preference in shared_preferences
- Use ARB files for translations
- Update UI language on change

### Notifications
- FCM push notifications for:
  - Enrollment confirmations
  - Course updates
  - Quiz reminders
  - Payment confirmations
- Handle notification taps
- Show in-app notifications

### Error Handling
- Show user-friendly error messages
- Retry button for failed requests
- Timeout handling
- Network connectivity check
- Show "No Internet" banner when offline
- Auto-retry when connection restored

### Loading States
- Shimmer effects for lists
- Circular progress for full-screen
- Disabled buttons with spinner during API calls
- Skeleton screens for detail pages

### Empty States
- No courses: "Browse our courses" button
- No enrollments: "Start learning today" button
- No quizzes: "No quizzes available yet"
- No results: "Try different filters"

## Security
- Use HTTPS for all API calls
- Store tokens in secure storage
- Clear sensitive data on logout
- Certificate pinning (optional)
- Root/jailbreak detection (optional)
- Prevent screenshots during quizzes

## Performance
- Lazy loading for long lists
- Image caching with cached_network_image
- Release controllers in dispose
- Optimize images before upload
- Use const widgets where possible

## Testing
- Unit tests for providers
- Widget tests for screens
- Integration tests for key flows
- Test login, enrollment, quiz submission, payment

## Build Configuration
- Create app flavors: dev, staging, prod
- Different API URLs per flavor
- Different app icons per flavor
- Version: 1.0.0+1 (build_number increments)
- Generate APK and AppBundle
- Generate IPA for iOS

---
Generate a complete, production-ready Flutter app with all the features, screens, and integrations specified above. Use Clean Architecture with proper separation of concerns. Include all necessary files for a working Flutter project.
