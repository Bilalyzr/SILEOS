import { signInWithPopup, signInWithRedirect, getRedirectResult, signOut as firebaseSignOut } from 'firebase/auth'
import { getAuthInstance, getGoogleProviderInstance } from '@/lib/firebase'
import { useAuthStore } from '@/store/auth'
import { authAPI } from '@/api/auth'
import toast from 'react-hot-toast'
import { useEffect, useState } from 'react'

/** Result of a Google sign-in attempt that did NOT produce a session. */
export interface GoogleOtpRequired {
  otpRequired: true
}

export interface UseGoogleOAuthReturn {
  /** Attempts sign-in. Resolves (instead of throwing) with
   *  `{ otpRequired: true }` when the account has 2FA enabled — the caller
   *  should reveal the code field and call completeGoogleSignInWithOtp. */
  signInWithGoogle: () => Promise<{ isNewUser: boolean } | GoogleOtpRequired | void>
  signOut: () => Promise<void>
  isLoading: boolean
  pendingGoogleUser: { email: string; token: string; name?: string; picture?: string } | null
  completeGoogleSignIn: (role: 'student' | 'instructor', phone: string) => Promise<void>
  /** Firebase ID token awaiting a TOTP code, or null when no 2FA challenge
   *  is in flight. Truthy state = show the Google OTP input. */
  pendingOtpToken: string | null
  /** Re-submit the held Firebase token + the user's TOTP code to
   *  /auth/google. Throws on a wrong code so the UI can flag the field. */
  completeGoogleSignInWithOtp: (otpCode: string) => Promise<void>
  /** Abandon an in-flight Google 2FA challenge. */
  cancelGoogleOtp: () => void
}

/** True when the backend answered the Google login with the password flow's
 *  pending-2FA marker (401 + detail "otp_required"). */
function isOtpRequiredError(error: any): boolean {
  if (error?.response?.status === 401 && error?.response?.data?.detail === 'otp_required') {
    return true
  }
  // Defensive: tolerate any 401 carrying the marker anywhere in the body
  // (same "includes" tolerance the password form applies to error text).
  const detail = error?.response?.data?.detail
  return error?.response?.status === 401 && typeof detail === 'string' && detail.includes('otp_required')
}

export function useGoogleOAuth(): UseGoogleOAuthReturn {
  const { logout, isLoading } = useAuthStore()
  const [pendingGoogleUser, setPendingGoogleUser] = useState<{ email: string; token: string; name?: string; picture?: string } | null>(null)
  const [pendingOtpToken, setPendingOtpToken] = useState<string | null>(null)

  // Handle redirect result when page loads after redirect
  useEffect(() => {
    const handleRedirectResult = async () => {
      // Hoisted so the catch can hold it for the 2FA re-submit.
      let idToken: string | null = null
      try {
        const result = await getRedirectResult(getAuthInstance())
        if (result) {
          const user = result.user

          idToken = await user.getIdToken()

          // Call Google sign-in API directly to handle new user case (pass fresh idToken)
          const response = await authAPI.googleSignIn(idToken)

          if ('new_user' in response) {
            // New user - set pending state for role selection (token is now in response)
            setPendingGoogleUser({
              email: response.email,
              token: response.token,
              name: response.name,
              picture: response.picture,
            })
          } else {
            // Existing user - use auth store to set state
            const authStore = await import('@/store/auth').then(m => m.useAuthStore.getState())
            authStore.setAuthState({
              user: response.user,
              profile: response.profile,
              instructorProfile: response.instructorProfile || null,
              accessToken: response.accessToken,
              refreshToken: response.refreshToken,
            })
            toast.success('Signed in with Google successfully!')
          }
        }
      } catch (error: any) {
        console.error('[DEBUG] Redirect result error:', error?.code, error)
        if (isOtpRequiredError(error)) {
          // 2FA challenge on the redirect path: the token we just got from
          // getRedirectResult is fresh, so hold it and let the caller reveal
          // the code field (axios errors carry no .code — check this BEFORE
          // the Firebase-code branch below).
          setPendingOtpToken(idToken)
          return
        }
        // Ignore errors about no pending redirect; surface the real code otherwise.
        if (error.code && error.code !== 'auth/no-pending-redirect') {
          if (error.code === 'auth/unauthorized-domain') {
            toast.error('This domain is not authorized for Google sign-in (Firebase → Authentication → Authorized domains).')
          } else {
            toast.error(`Google sign-in failed (${error.code}). Try email/password.`)
          }
        }
      }
    }

    handleRedirectResult()
  }, [])

  const signInWithGoogle = async (): Promise<{ isNewUser: boolean } | GoogleOtpRequired | void> => {
    // Held outside the try so the otp_required catch can keep it for the
    // 2FA re-submit (the backend needs the SAME Firebase token + the code).
    let idToken: string | null = null
    try {
      // First try popup
      const result = await signInWithPopup(getAuthInstance(), getGoogleProviderInstance())
      const user = result.user

      // Get ID token for backend verification
      idToken = await user.getIdToken()

      // Call Google sign-in API directly to handle new user case (pass fresh idToken)
      const response = await authAPI.googleSignIn(idToken)

      if ('new_user' in response) {
        // New user - set pending state for role selection (token is now in response)
        setPendingGoogleUser({
          email: response.email,
          token: response.token,
          name: response.name,
          picture: response.picture,
        })
        return { isNewUser: true }
      }

      // Existing user - use auth store to set state
      const authStore = await import('@/store/auth').then(m => m.useAuthStore.getState())
      authStore.setAuthState({
        user: response.user,
        profile: response.profile,
        instructorProfile: response.instructorProfile || null,
        accessToken: response.accessToken,
        refreshToken: response.refreshToken,
      })

      toast.success('Signed in with Google successfully!')
      return { isNewUser: false }
    } catch (error: any) {
      console.error('Google sign-in error:', error)

      // 2FA gate (parity with the password login): the backend verified the
      // Google credential but the account has TOTP enrolled. Hold the ID
      // token, tell the caller to reveal the code field — NOT an error toast.
      if (isOtpRequiredError(error)) {
        setPendingOtpToken(idToken)
        return { otpRequired: true }
      }

      console.error('Error code:', error.code)
      console.error('Error message:', error.message)
      console.error('Error details:', error)

      // If popup fails, fall back to redirect
      if (error.code === 'auth/popup-closed-by-user' || error.code === 'auth/popup-blocked') {
        toast('Opening Google sign-in in a new window...')
        await signInWithRedirect(getAuthInstance(), getGoogleProviderInstance())
        return
      }

      // Handle specific Firebase errors
      if (error.code === 'auth/account-exists-with-different-credential') {
        toast.error('An account already exists with the same email address using a different sign-in method.')
      } else if (error.code === 'auth/user-disabled') {
        toast.error('This account has been disabled. Please contact support.')
      } else if (error.code === 'auth/operation-not-allowed') {
        toast.error('Google sign-in is not enabled. Please contact support.')
      } else if (error.code === 'auth/invalid-api-key') {
        toast.error('Authentication service is not properly configured. Please contact support.')
      } else if (error.code === 'auth/unauthorized-domain') {
        toast.error('This domain is not authorized for Google sign-in. Add it in Firebase → Authentication → Authorized domains.')
      } else if (error.code === 'auth/network-request-failed') {
        toast.error('Google sign-in network error — try email/password, or a different browser/network.')
      } else {
        // Surface the real Firebase error code instead of a generic message.
        const code = error?.code ? ` (${error.code})` : ''
        toast.error(`Google sign-in failed${code}. Try email/password, or open in Chrome/Safari.`)
      }

      throw error
    }
  }

  const completeGoogleSignInWithOtp = async (otpCode: string) => {
    if (!pendingOtpToken) {
      throw new Error('No pending Google sign-in')
    }

    // Re-submit the SAME endpoint with the held Firebase token + the code —
    // the exact inline-otp_code completion the password login uses.
    const response = await authAPI.googleSignIn(pendingOtpToken, undefined, otpCode)
    if ('new_user' in response) {
      // Unreachable: a 2FA-challenged account exists by definition, so the
      // backend can never answer the completion with new_user.
      throw new Error('Unexpected new-user response during 2FA completion')
    }

    const authStore = await import('@/store/auth').then(m => m.useAuthStore.getState())
    authStore.setAuthState({
      user: response.user,
      profile: response.profile,
      instructorProfile: response.instructorProfile || null,
      accessToken: response.accessToken,
      refreshToken: response.refreshToken,
    })

    setPendingOtpToken(null)
    toast.success('Signed in with Google successfully!')
  }

  const cancelGoogleOtp = () => {
    setPendingOtpToken(null)
  }

  const completeGoogleSignIn = async (role: 'student' | 'instructor', phone: string) => {
    if (!pendingGoogleUser) {
      throw new Error('No pending Google sign-in')
    }

    const response = await authAPI.completeGoogleSignIn({
      email: pendingGoogleUser.email,
      role,
      googleToken: pendingGoogleUser.token,
      phone,
    })

    // Set auth state with completed user
    const authStore = await import('@/store/auth').then(m => m.useAuthStore.getState())
    authStore.setAuthState({
      user: response.user,
      profile: response.profile,
      instructorProfile: response.instructorProfile || null,
      accessToken: response.accessToken,
      refreshToken: response.refreshToken,
    })

    // Clear pending state
    setPendingGoogleUser(null)

    toast.success('Account created successfully!')
  }

  const signOut = async () => {
    try {
      await firebaseSignOut(getAuthInstance())
      logout()
      toast.success('Signed out successfully!')
    } catch (error) {
      console.error('Firebase sign-out error:', error)
      // Still logout from app state even if Firebase sign-out fails
      logout()
    }
  }

  return {
    signInWithGoogle,
    signOut,
    isLoading,
    pendingGoogleUser,
    completeGoogleSignIn,
    pendingOtpToken,
    completeGoogleSignInWithOtp,
    cancelGoogleOtp,
  }
}
