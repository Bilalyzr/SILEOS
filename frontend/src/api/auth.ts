import { api } from './axios'
import { User,UserProfile,InstructorProfile,LoginForm,RegisterForm } from '@/types'

interface AuthResponse {
  user: User
  profile: UserProfile
  instructorProfile?: InstructorProfile
  accessToken: string
  refreshToken: string
}

interface RefreshTokenResponse {
  accessToken: string
  refreshToken: string
}

export const authAPI = {
  // Login user
  login: async (credentials: LoginForm): Promise<AuthResponse> => {
    const response = await api.post(`/auth/login`, credentials)
    const data = response.data

    return {
      user: data.user,
      profile: data.profile || {} as UserProfile,
      instructorProfile: data.instructorProfile || undefined,
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    }
  },

  // Register user
  register: async (data: RegisterForm): Promise<AuthResponse> => {
    const body: Record<string, unknown> = {
      username: data.email.split('@')[0],
      email: data.email,
      password: data.password,
      first_name: data.first_name,
      last_name: data.last_name,
      user_type: data.user_type,
    }
    if (data.phone) body.phone = data.phone
    if (data.user_type === 'instructor') {
      if (data.bio) body.bio = data.bio
      if (data.designation) body.designation = data.designation
    }

    const response = await api.post(`/auth/register`, body)
    const result = response.data

    return {
      user: result,
      profile: {} as UserProfile,
      instructorProfile: undefined,
      accessToken: '', // Will need to login after registration
      refreshToken: '',
    }
  },

  // Logout user
  logout: async (refreshToken: string): Promise<void> => {
    await api.post(`/auth/logout`, { refreshToken })
  },

  // Refresh access token
  refreshToken: async (refreshToken: string): Promise<RefreshTokenResponse> => {
    const response = await api.post(`/auth/refresh`, { refresh_token: refreshToken })
    const data = response.data

    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    }
  },

  // Get current user
  getCurrentUser: async (_accessToken: string): Promise<{
    user: User
    profile: UserProfile
    instructorProfile?: InstructorProfile
  }> => {
    // /auth/me is the source of truth for identity (name + role) and MUST
    // load. The profile call is secondary — a failing /users/profile must not
    // prevent the user from loading (that's what made the dashboard show
    // "You"). /auth/me already embeds a profile object, so fall back to it.
    const userResponse = await api.get(`/auth/me`)
    const me = userResponse.data.user || userResponse.data

    let profile: any = me.profile || {}
    let instructorProfile: any = me.instructorProfile || undefined
    try {
      const profileResponse = await api.get(`/users/profile`)
      profile = profileResponse.data.profile || profileResponse.data || profile
      instructorProfile = profileResponse.data.instructorProfile || instructorProfile
    } catch (e) {
      console.warn('getCurrentUser: profile fetch failed, using /auth/me profile', e)
    }

    return { user: me, profile, instructorProfile }
  },

  // Update user profile
  updateProfile: async (
    profileData: Partial<UserProfile>
  ): Promise<UserProfile> => {
    const response = await api.put(`/auth/profile`, profileData)
    return response.data.data || response.data
  },

  // Change password
  changePassword: async (
    data: { currentPassword: string; newPassword: string }
  ): Promise<void> => {
    await api.post(`/auth/change-password`, {
      current_password: data.currentPassword,
      new_password: data.newPassword
    })
  },

  // Forgot password
  forgotPassword: async (email: string): Promise<void> => {
    await api.post(`/auth/forgot-password`, { email })
  },

  // Reset password
  resetPassword: async (token: string, newPassword: string): Promise<void> => {
    await api.post(`/auth/reset-password`, {
      token,
      newPassword,
    })
  },

  // Verify email
  verifyEmail: async (token: string): Promise<void> => {
    await api.post(`/auth/verify-email`, { token })
  },

  // Resend verification email
  resendVerificationEmail: async (email: string): Promise<void> => {
    await api.post(`/auth/resend-verification`, { email })
  },

  // Social login (Google, Facebook, etc.)
  socialLogin: async (provider: string, token: string): Promise<AuthResponse> => {
    const response = await api.post(`/auth/social/${provider}`, { token })
    return response.data.data
  },

  // Google OAuth login - get idToken from Firebase and send to backend.
  // `otpCode` completes a 2FA-gated Google sign-in: the backend answers
  // 401 "otp_required" for TOTP-enrolled accounts, and the client re-submits
  // the SAME token plus the current code (mirrors the password login's
  // inline otp_code re-submit).
  googleSignIn: async (idToken: string, originalToken?: string, otpCode?: string): Promise<AuthResponse | { new_user: true; email: string; name: string; picture: string; token: string }> => {
    try {
      const body: Record<string, string> = { token: idToken }
      if (otpCode) body.otp_code = otpCode
      const response = await api.post(`/auth/google`, body)
      // Backend returns data directly, not in response.data.data
      const data = response.data

      // Check if this is a new user
      if (data.new_user === true) {
        // Include the original idToken for completing the sign-in
        return { new_user: true, email: data.email, name: data.name, picture: data.picture, token: originalToken || idToken }
      }

      return {
        user: data.user,
        profile: data.profile || {} as UserProfile,
        instructorProfile: data.instructorProfile || undefined,
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
      }
    } catch (error: any) {
      console.error('[DEBUG] /auth/google error:', error.response?.status, error.response?.data)
      throw error
    }
  },

  // Check if email exists
  checkEmail: async (email: string): Promise<{ exists: boolean }> => {
    const response = await api.post(`/auth/check-email`, { email })
    return response.data.data
  },

  // Get user roles
  getUserRoles: async (): Promise<string[]> => {
    const response = await api.get(`/auth/roles`)
    return response.data.data
  },

  // Update instructor profile
  updateInstructorProfile: async (
    profileData: Partial<InstructorProfile>
  ): Promise<InstructorProfile> => {
    const response = await api.put(`/auth/instructor-profile`, profileData)
    return response.data.data
  },

  // Complete Google sign-in with role selection (for new users). Google never
  // returns a phone number, so it is collected in the same step and is required.
  completeGoogleSignIn: async (data: { email: string; role: 'student' | 'instructor'; googleToken: string; phone: string }): Promise<AuthResponse> => {
    const response = await api.post(`/auth/google/complete`, {
      google_token: data.googleToken,
      role: data.role,
      phone: data.phone
    })
    const result = response.data.data || response.data
    return {
      user: result.user,
      profile: result.profile || {} as UserProfile,
      instructorProfile: result.instructorProfile || undefined,
      accessToken: result.access_token,
      refreshToken: result.refresh_token,
    }
  },

  // Save the mobile number for the logged-in user. Used by the one-time
  // prompt shown to Google accounts created before the number was mandatory.
  setPhoneNumber: async (phone: string): Promise<string> => {
    const response = await api.post(`/auth/phone`, { phone })
    return response.data?.phone ?? phone
  },

  // --- Two-factor authentication (TOTP) -------------------------------
  // Mirrors the backend's /auth/2fa/* endpoints. Enrolment is two-step:
  // setup() stores a pending secret (totp_enabled stays false), then
  // enable() confirms with a live code to flip enforcement on.
  setupTwoFactor: async (): Promise<{ secret: string; otpauth_uri: string }> => {
    const res = await api.post(`/auth/2fa/setup`)
    return res.data
  },

  enableTwoFactor: async (code: string): Promise<{ totp_enabled: boolean }> => {
    const res = await api.post(`/auth/2fa/enable`, { code })
    return res.data
  },

  disableTwoFactor: async (code: string): Promise<{ totp_enabled: boolean }> => {
    const res = await api.post(`/auth/2fa/disable`, { code })
    return res.data
  },
}