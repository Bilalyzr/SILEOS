# Google Auth Flow Redesign

**Date:** 2026-05-05
**Status:** Approved

## Overview

Improve the Google OAuth sign-in flow with a role selection modal for new users and clean up the login/signup UI.

## Current Behavior

1. Login page: Has email/password form + "Or continue with" section with Google/LinkedIn buttons
2. Signup page: Has full registration form, Google button exists but flow is unclear
3. Google sign-in: Creates account immediately as "student" role, no role selection
4. Backend: Firebase token verification is broken (credentials error)

## New Behavior

### Login Page (`/login`)

**Changes:**
- Remove "Or continue with" heading
- Change Google button text to "Sign in with Google"
- Keep email/password form, Remember me, Forgot password
- Keep LinkedIn button with current text

**Flow:**
1. User clicks "Sign in with Google"
2. Firebase popup opens, user authenticates
3. Frontend sends ID token to `/api/v1/auth/google`
4. Backend verifies token:
   - If user exists: Return auth tokens, redirect to dashboard
   - If user doesn't exist: Return special response `{ new_user: true, email: string }`
5. Frontend shows role selection modal
6. User selects role → modal sends selected role to backend
7. Backend creates account with selected role → returns auth tokens

### Signup Page (`/register`)

**Changes:**
- Keep all existing form fields (email, password, first name, last name, etc.)
- Add "Continue with Google" button (same styling as login page)
- Remove any existing "Or continue with" text if present

**Flow:**
1. User can either:
   - Fill out form and click "Sign up" (existing flow)
   - Click "Continue with Google" → same role modal flow as login page

### Role Selection Modal (New Component)

**Component:** `RoleSelectionModal`

**Props:**
- `isOpen: boolean`
- `onClose: () => void`
- `onSelect: (role: 'student' | 'instructor') => void`
- `email: string` (user's Google email)
- `loading: boolean`

**UI Structure:**
```
┌─────────────────────────────────────────┐
│  ×                                      │
│                                         │
│  Create your account                    │
│  Join thousands of learners and         │
│  start your journey today               │
│                                         │
│  I want to join as:                     │
│                                         │
│  ┌──────────────┐  ┌──────────────┐   │
│  │  🎓 Student  │  │  👨‍🏫 Instructor│   │
│  │              │  │              │   │
│  │ Learn from   │  │ Teach & earn │   │
│  │ experts      │  │              │   │
│  └──────────────┘  └──────────────┘   │
│                                         │
│            [ Continue ]                │
└─────────────────────────────────────────┘
```

**Behavior:**
- Cards highlight on hover
- Selected card has visual indicator (border/shadow)
- "Continue" button disabled until role selected
- Clicking X closes modal and cancels flow
- Pressing Escape closes modal

### Backend Changes

**Endpoint:** `POST /api/v1/auth/google`

**Current flow:** Always creates/returns user
**New flow:**
1. Verify Firebase ID token (fix verification method)
2. Check if user exists by email
3. If exists: Return full auth response (existing behavior)
4. If not exists: Return `{ new_user: true, email: string, temp_token?: string }`

**New Endpoint:** `POST /api/v1/auth/google/complete`

**Request body:**
```json
{
  "email": "user@gmail.com",
  "role": "student" | "instructor",
  "google_token": "firebase_id_token"
}
```

**Response:** Standard auth response (access_token, refresh_token, user, profile)

**Firebase Token Verification Fix:**

Current implementation uses Firebase Admin SDK which requires service account credentials. New implementation uses manual JWT verification with Google's public certificates:

```python
import jwt
import requests

def verify_firebase_token(id_token: str) -> dict:
    # 1. Decode without verification to get kid
    header = jwt.get_unverified_header(id_token)

    # 2. Get Google's public keys
    keys_url = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
    keys_response = requests.get(keys_url)
    keys = keys_response.json()

    # 3. Find matching key by kid
    public_key = keys[header['kid']]

    # 4. Verify token
    decoded = jwt.decode(
        id_token,
        public_key,
        algorithms=['RS256'],
        audience=firebase_project_id,
        issuer=f"https://securetoken.google.com/{firebase_project_id}"
    )

    return decoded
```

## Files to Modify

### Frontend
1. `frontend/src/components/auth/login-form.tsx`
   - Remove "Or continue with" text
   - Update Google button text

2. `frontend/src/components/auth/unified-register-form.tsx`
   - Add "Continue with Google" button

3. `frontend/src/components/auth/RoleSelectionModal.tsx` (NEW)
   - Create modal component

4. `frontend/src/hooks/use-google-oauth.tsx`
   - Handle new_user response
   - Show/hide role modal

5. `frontend/src/api/auth.ts`
   - Add `completeGoogleSignIn()` function

### Backend
1. `backend/app/routers/auth.py`
   - Rewrite `/google` endpoint to return new_user flag
   - Add `/google/complete` endpoint
   - Replace Firebase Admin SDK with manual JWT verification

2. `backend/app/requirements.txt`
   - Add `pyjwt` if not present

## Success Criteria

1. Login page no longer shows "Or continue with" text
2. New Google users see role selection modal before account creation
3. Existing Google users log in directly without modal
4. Signup page has working Google button
5. Firebase token verification works without service account credentials
6. Users can successfully sign up as Student or Instructor via Google

## Edge Cases

1. **User closes role modal**: Auth flow is cancelled, user returns to login
2. **Token expires during modal**: Show error, ask user to try again
3. **Email already verified**: Google users auto-verified (is_verified=True)
4. **Instructor approval flow**: Instructors still require admin approval (existing behavior)
