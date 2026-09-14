import * as React from "react"
import { Link, useNavigate, useLocation, useSearchParams } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Eye, EyeOff, Mail, Lock, Loader2, ShieldCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/hooks/use-auth"
import { useGoogleOAuth } from "@/hooks/use-google-oauth"
import { isFirebaseConfigured } from "@/lib/firebase"
import { RoleSelectionModal } from "@/components/auth/RoleSelectionModal"
import { LoginForm as LoginFormType } from "@/types"
import { roleHomePath, isNonStudentRole } from "@/utils/role-routing"
import toast from "react-hot-toast"

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(6, "Password must be at least 6 characters"),
  remember: z.boolean().optional(),
  // Only required once the server has answered "otp_required"; left optional
  // here so the first submit (which discovers whether 2FA applies) validates.
  otp_code: z.string().optional(),
})

export const LoginForm: React.FC = () => {
  const [showPassword, setShowPassword] = React.useState(false)
  // Tracks whether the last login attempt failed because the user is
  // unverified. Drives the inline "Resend verification email" button
  // so users stuck after an SMTP outage can retrigger delivery.
  const [unverifiedEmail, setUnverifiedEmail] = React.useState<string | null>(null)
  const [resendingVerification, setResendingVerification] = React.useState(false)
  // Set once the server answers 401 "otp_required" — reveals the code field
  // and keeps it visible while the user fetches a code from their app.
  const [otpRequired, setOtpRequired] = React.useState(false)
  const { login, isLoading, error, clearError } = useAuth()
  const {
    signInWithGoogle,
    isLoading: isGoogleLoading,
    pendingGoogleUser,
    pendingOtpToken,
    completeGoogleSignInWithOtp,
    cancelGoogleOtp,
  } = useGoogleOAuth()
  // Google 2FA completion state — the backend answered the Google sign-in
  // with the SAME "otp_required" marker the password flow uses; the held
  // Firebase token + this code finish the login.
  const [googleOtp, setGoogleOtp] = React.useState("")
  const [googleOtpError, setGoogleOtpError] = React.useState<string | null>(null)
  const [completingGoogleOtp, setCompletingGoogleOtp] = React.useState(false)
  const [isRoleModalOpen, setIsRoleModalOpen] = React.useState(false)
  const [, setSelectedRole] = React.useState<'student' | 'instructor' | null>(null)
  const [completingGoogleAuth, setCompletingGoogleAuth] = React.useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()

  // Resolve the post-login destination for student/default-role users:
  // 1) `?redirect=` query param (sent by membership.tsx, bundle-detail.tsx,
  //    course-detail.tsx when an anonymous visitor tries to buy/subscribe),
  //    restricted to same-origin relative paths to prevent an open redirect
  //    (must start with "/" and not "//", which browsers treat as
  //    protocol-relative and would send the user off-site);
  // 2) the react-router "from" location (set by ProtectedRoute-style guards);
  // 3) undefined, so callers fall back to the role-based default ('/dashboard').
  const getRedirectTarget = React.useCallback((): string | undefined => {
    const redirectParam = searchParams.get("redirect")
    if (redirectParam && redirectParam.startsWith("/") && !redirectParam.startsWith("//")) {
      return redirectParam
    }
    return (location.state as any)?.from?.pathname
  }, [searchParams, location.state])

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
    getValues,
  } = useForm<LoginFormType>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
      remember: false,
    },
  })

  const handleResendVerification = async () => {
    const email = unverifiedEmail || getValues("email")
    if (!email) {
      toast.error("Enter your email first")
      return
    }
    setResendingVerification(true)
    try {
      const res = await fetch("/api/v1/auth/resend-verification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      })
      if (res.ok) {
        toast.success("Verification email sent — check your inbox (and spam folder).", { duration: 6000 })
      } else {
        const data = await res.json().catch(() => ({}))
        toast.error(data.detail || "Failed to resend verification email")
      }
    } catch (e) {
      console.error(e)
      toast.error("Failed to resend verification email")
    } finally {
      setResendingVerification(false)
    }
  }

  // Clear errors when component mounts
  React.useEffect(() => {
    clearError()
  }, [clearError])

  // Show message if redirected from profile completion
  React.useEffect(() => {
    const state = location.state as any
    if (state?.message) {
      toast.success(state.message, { duration: 4000 })
      // Clear the state to prevent showing message on refresh
      window.history.replaceState({}, document.title)
    }
  }, [location.state])

  // Show role modal when pending Google user exists
  React.useEffect(() => {
    if (pendingGoogleUser) {
      setIsRoleModalOpen(true)
    }
  }, [pendingGoogleUser])

  // Handle server errors
  React.useEffect(() => {
    if (error) {
      // Check for specific error messages from backend
      // Machine-readable marker from the backend's 2FA gate — this is a
      // prompt for a second factor, not a credential failure, so don't
      // surface the raw token as a toast.
      if (error.includes("otp_required")) {
        setOtpRequired(true)
      } else if (error.includes("authentication code")) {
        setOtpRequired(true)
        setError("otp_code", { message: "That code didn't match. Try the current one." })
      } else if (error.includes("verify your email") || error.includes("verification")) {
        toast.error(error, { duration: 6000 })
        // Remember the email the user just tried so the inline Resend
        // button below the form has a target.
        const attempted = getValues("email")
        if (attempted) setUnverifiedEmail(attempted)
      } else if (error.includes("No account found")) {
        setError("email", { message: "No account found with this email address" })
      } else if (error.includes("Invalid email or password")) {
        setError("password", { message: "Incorrect email or password" })
      } else if (error.includes("Incorrect password") || error.includes("password")) {
        setError("password", { message: "Incorrect password. Please try again" })
      } else if (error.includes("pending approval")) {
        toast.error(error, { duration: 6000 })
      } else {
        toast.error(error)
      }
    }
  }, [error, getValues, setError])

  const onSubmit = async (data: LoginFormType) => {
    try {
      clearError()
      await login(data)
      toast.success("Welcome back!")

      // Grab the fresh role from the auth store (the store writes are
      // synchronous after login() resolves).
      const authStore = await import('@/store/auth').then(m => m.useAuthStore.getState())
      const userRole = authStore.user?.role

      // For non-student roles we ALWAYS redirect to the role dashboard — never
      // honour `from`, because `from` may point at a student-only page like
      // /dashboard that would confuse the SPOC / company / instructor / admin.
      if (isNonStudentRole(userRole)) {
        navigate(roleHomePath(userRole), { replace: true })
        return
      }

      // Student: honour "come-from" if set, else go to student dashboard.
      const from = getRedirectTarget()
      navigate(from || '/dashboard', { replace: true })
    } catch (err: any) {
      // Error handling is done in the useEffect above
      console.error("Login error:", err)
      console.error("Error response:", err.response?.data)
      console.error("Error message:", err.message)
    }
  }

  const handleGoogleLogin = async () => {
    try {
      setGoogleOtpError(null)
      const result = await signInWithGoogle()

      // 2FA gate: the backend verified the Google credential but the
      // account has TOTP enrolled. The OTP panel below is revealed by the
      // hook setting pendingOtpToken — this is a prompt, not a failure.
      if (result && 'otpRequired' in result) {
        return
      }

      // If result is undefined or isNewUser is false, proceed with login flow
      if (!result || result.isNewUser === false) {
        toast.success("Welcome back!")

        const authStore = await import('@/store/auth').then(m => m.useAuthStore.getState())
        const userRole = authStore.user?.role

        if (isNonStudentRole(userRole)) {
          navigate(roleHomePath(userRole), { replace: true })
          return
        }

        const from = getRedirectTarget()
        navigate(from || '/dashboard', { replace: true })
      }
      // If isNewUser is true, the modal will open automatically via useEffect
    } catch (err: any) {
      // Error handling is done in the hook
      console.error("Google login error:", err)
    }
  }

  // Complete a 2FA-gated Google sign-in: re-submit the held Firebase token
  // with the user's authenticator code (the same inline otp_code completion
  // the password login performs), then route exactly like a normal login.
  const onSubmitGoogleOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    const code = googleOtp.trim()
    if (!/^\d{6}$/.test(code)) {
      setGoogleOtpError("Enter the 6-digit code from your authenticator app.")
      return
    }

    setCompletingGoogleOtp(true)
    setGoogleOtpError(null)
    try {
      await completeGoogleSignInWithOtp(code)
      setGoogleOtp("")

      const authStore = await import('@/store/auth').then(m => m.useAuthStore.getState())
      const userRole = authStore.user?.role

      if (isNonStudentRole(userRole)) {
        navigate(roleHomePath(userRole), { replace: true })
        return
      }
      const from = getRedirectTarget()
      navigate(from || '/dashboard', { replace: true })
    } catch (err: any) {
      console.error("Google 2FA completion error:", err)
      const detail: string = err?.response?.data?.detail || err?.message || ""
      if (detail.includes("authentication code")) {
        // Wrong code — keep the panel open so the user can retry.
        setGoogleOtpError("That code didn't match. Try the current one.")
      } else if (detail.includes("otp_required")) {
        setGoogleOtpError("Your account still needs a code. Enter the current one.")
      } else {
        // e.g. the held Firebase token expired (they are valid ~1h) — the
        // cleanest recovery is a fresh Google sign-in.
        setGoogleOtpError(detail || "Could not complete sign-in. Start Google sign-in again.")
      }
    } finally {
      setCompletingGoogleOtp(false)
    }
  }

  const handleCancelGoogleOtp = () => {
    setGoogleOtp("")
    setGoogleOtpError(null)
    cancelGoogleOtp()
  }

  const handleRoleSelect = async (role: 'student' | 'instructor', phone: string) => {
    if (!pendingGoogleUser) return

    setCompletingGoogleAuth(true)
    setSelectedRole(role)

    try {
      const { authAPI } = await import('@/api/auth')
      const response = await authAPI.completeGoogleSignIn({
        email: pendingGoogleUser.email,
        role: role,
        googleToken: pendingGoogleUser.token,
        phone
      })

      // Update auth store with response using the setAuthState method
      const { useAuthStore } = await import('@/store/auth')
      useAuthStore.getState().setAuthState({
        user: response.user,
        profile: response.profile,
        instructorProfile: response.instructorProfile ?? null,
        accessToken: response.accessToken,
        refreshToken: response.refreshToken,
      })

      setIsRoleModalOpen(false)
      toast.success(`Account created successfully! Welcome as ${role === 'instructor' ? 'Instructor' : 'Student'}.`)

      // Navigate based on role
      navigate(roleHomePath(role), { replace: true })
    } catch (err: any) {
      console.error('Complete Google auth error:', err)
      toast.error(err.response?.data?.detail || 'Failed to complete sign up. Please try again.')
      setSelectedRole(null)
    } finally {
      setCompletingGoogleAuth(false)
    }
  }

  const handleRoleModalClose = () => {
    if (!completingGoogleAuth) {
      setIsRoleModalOpen(false)
      setSelectedRole(null)
    }
  }

  const handleLinkedInLogin = () => {
    const clientId = '869qrsv3ufb6x5'
    const redirectUri = encodeURIComponent('https://lms.sashainfinity.com/auth/linkedin/callback')
    const scope = encodeURIComponent('openid profile email')
    const state = Math.random().toString(36).substring(7)
    localStorage.setItem('linkedin_state', state)
    window.location.href = `https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=${clientId}&redirect_uri=${redirectUri}&scope=${scope}&state=${state}`
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-secondary-50 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">Welcome back</CardTitle>
          <CardDescription className="text-center">
            Sign in to your account to continue learning
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Email Input */}
            <div className="space-y-2">
              <Input
                {...register("email")}
                type="email"
                placeholder="Enter your email"
                leftIcon={<Mail className="w-4 h-4" />}
                error={errors.email?.message}
                disabled={isSubmitting || isLoading}
                className="h-12"
              />
            </div>

            {/* Password Input */}
            <div className="space-y-2">
              <div className="relative">
                <Input
                  {...register("password")}
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  leftIcon={<Lock className="w-4 h-4" />}
                  error={errors.password?.message}
                  disabled={isSubmitting || isLoading}
                  className="h-12"
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-neutral-500 hover:text-neutral-700 p-2 min-h-[44px] min-w-[44px] flex items-center justify-center"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={isSubmitting || isLoading}
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Two-factor code — revealed only after the server says this
                account has 2FA enabled, so ordinary logins are unaffected.
                Suppressed while a GOOGLE 2FA challenge is in flight so only
                one code field shows at a time. */}
            {otpRequired && !pendingOtpToken && (
              <div className="space-y-2">
                <label htmlFor="otp_code" className="text-sm font-medium text-neutral-700">
                  Authentication code
                </label>
                <Input
                  {...register("otp_code")}
                  id="otp_code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={8}
                  placeholder="6-digit code"
                  leftIcon={<ShieldCheck className="w-4 h-4" />}
                  error={errors.otp_code?.message}
                  disabled={isSubmitting || isLoading}
                  className="h-12 tracking-widest"
                  autoFocus
                />
                <p className="text-xs text-neutral-500">
                  Open your authenticator app and enter the current code for SashaInfinity LMS.
                </p>
              </div>
            )}

            {/* Remember Me & Forgot Password */}
            <div className="flex items-center justify-between gap-4">
              <label className="flex items-center touch-action-manipulation">
                <input
                  {...register("remember")}
                  type="checkbox"
                  className="rounded border-neutral-300 text-primary-600 focus:ring-primary-500 w-5 h-5"
                  disabled={isSubmitting || isLoading}
                />
                <span className="ml-2 text-sm text-neutral-600">Remember me</span>
              </label>
              <Link
                to="/forgot-password"
                className="text-sm text-primary-600 hover:text-primary-700 min-h-[44px] flex items-center"
              >
                Forgot password?
              </Link>
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              className="w-full h-12 sm:h-10"
              disabled={isSubmitting || isLoading}
              loading={isSubmitting || isLoading}
            >
              {isSubmitting || isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign in"
              )}
            </Button>
          </form>

          {/* Google sign-in + 2FA: the backend answered the Google credential
              with the SAME "otp_required" marker the password login uses.
              Same code-input pattern; submitting re-sends the held Google
              token with the code to /auth/google. Kept OUTSIDE the password
              form — a nested form would be invalid HTML. */}
          {pendingOtpToken && (
            <form onSubmit={onSubmitGoogleOtp} className="mt-4 space-y-3 rounded-lg border border-primary-200 bg-primary-50/60 p-4">
              <div className="space-y-2">
                <label htmlFor="google_otp_code" className="text-sm font-medium text-neutral-700">
                  Authentication code (Google sign-in)
                </label>
                <Input
                  id="google_otp_code"
                  name="google_otp_code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={8}
                  placeholder="6-digit code"
                  leftIcon={<ShieldCheck className="w-4 h-4" />}
                  error={googleOtpError ?? undefined}
                  disabled={completingGoogleOtp}
                  className="h-12 tracking-widest"
                  value={googleOtp}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setGoogleOtp(e.target.value)}
                  autoFocus
                />
                <p className="text-xs text-neutral-500">
                  Google verified your account. Enter the current code from your
                  authenticator app to finish signing in.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <Button
                  type="submit"
                  className="h-10"
                  loading={completingGoogleOtp}
                  disabled={completingGoogleOtp}
                >
                  {completingGoogleOtp ? "Completing..." : "Complete sign-in"}
                </Button>
                <button
                  type="button"
                  onClick={handleCancelGoogleOtp}
                  disabled={completingGoogleOtp}
                  className="text-sm text-neutral-600 hover:text-neutral-800 min-h-[44px]"
                >
                  Use a different method
                </button>
              </div>
            </form>
          )}

          {unverifiedEmail && (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm">
              <p className="font-medium text-amber-900 mb-1">Email not verified yet</p>
              <p className="text-amber-800 mb-3">
                We sent a verification link to <span className="font-mono">{unverifiedEmail}</span>.
                If it never arrived (or the server had mail trouble earlier), request a fresh one.
              </p>
              <button
                type="button"
                onClick={handleResendVerification}
                disabled={resendingVerification}
                className="px-3 py-1.5 rounded-md bg-amber-600 text-white text-sm font-medium hover:bg-amber-700 disabled:opacity-50"
              >
                {resendingVerification ? "Sending…" : "Resend verification email"}
              </button>
            </div>
          )}

          {/* Divider */}
          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-neutral-300" />
              </div>
              <div className="relative flex justify-center text-sm">
              </div>
            </div>

            {/* Social Login Buttons */}
            <div className="mt-6 grid grid-cols-2 gap-3 sm:gap-4">
              <Button
                variant="outline"
                onClick={handleGoogleLogin}
                disabled={isSubmitting || isLoading || isGoogleLoading || !isFirebaseConfigured}
                title={!isFirebaseConfigured ? "Google sign-in not configured" : undefined}
                className="min-h-[44px] sm:min-h-0"
              >
                <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="currentColor"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                <span className="hidden sm:inline">Sign in with Google</span>
                <span className="sm:hidden">Google</span>
              </Button>
              <Button
                variant="outline"
                onClick={handleLinkedInLogin}
                disabled={isSubmitting || isLoading}
                className="min-h-[44px] sm:min-h-0"
              >
                <svg className="w-4 h-4 mr-2" fill="#0A66C2" viewBox="0 0 24 24">
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                </svg>
                LinkedIn
              </Button>
            </div>
          </div>

          {/* Sign up link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-neutral-600">
              Don't have an account?{" "}
              <Link
                to="/register"
                className="font-medium text-primary-600 hover:text-primary-700"
              >
                Sign up for free
              </Link>
            </p>
          </div>
        </CardContent>
      </Card>

      <RoleSelectionModal
        isOpen={isRoleModalOpen}
        onClose={handleRoleModalClose}
        onSelect={handleRoleSelect}
        email={pendingGoogleUser?.email}
        loading={completingGoogleAuth}
      />
    </div>
  )
}
