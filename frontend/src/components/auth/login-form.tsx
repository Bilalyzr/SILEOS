import * as React from "react"
import { Link, useNavigate, useLocation, useSearchParams } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { AnimatePresence, motion } from "framer-motion"
import { Mail, Lock, ShieldCheck, MailWarning } from "lucide-react"
import { GatewayField } from "@/components/auth/gateway/GatewayField"
import {
  GoogleMark,
  LinkedInMark,
  MagneticButton,
  PasswordField,
  ProviderCard,
} from "@/components/auth/gateway/GatewayControls"
import { useAuth } from "@/hooks/use-auth"
import { useGoogleOAuth } from "@/hooks/use-google-oauth"
import { isFirebaseConfigured } from "@/lib/firebase"
import { RoleSelectionModal } from "@/components/auth/RoleSelectionModal"
import { LoginForm as LoginFormType } from "@/types"
import { roleHomePath, isNonStudentRole } from "@/utils/role-routing"
import toast from "react-hot-toast"

const loginSchema = z.object({
  email: z.string().email("Enter the email you signed up with, like name@example.com."),
  password: z.string().min(6, "Your password has at least 6 characters."),
  remember: z.boolean().optional(),
  // Only required once the server has answered "otp_required"; left optional
  // here so the first submit (which discovers whether 2FA applies) validates.
  otp_code: z.string().optional(),
})

export const LoginForm: React.FC = () => {
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
    watch,
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
      } else if (error.includes("No account found") || error.includes("email")) {
        setError("email", { message: "We couldn't find an account with this email. Check the spelling, or create an account above." })
      } else if (error.includes("Incorrect password") || error.includes("password")) {
        setError("password", { message: "That password doesn't match. Try again, or reset it with Forgot password." })
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

  const emailValue = watch("email")
  const emailLooksValid = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(emailValue || "")
  const busy = isSubmitting || isLoading

  return (
    // AuthLayout (the gateway) owns the scene, panel and mode switch; this
    // component fills the panel.
    <div className="w-full">
      <div className="ag-head">
        <h2>Welcome back</h2>
        <p>Sign in to continue your learning path.</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="ag-form" noValidate>
        <GatewayField
          {...register("email")}
          id="login_email"
          label="Email address"
          type="email"
          autoComplete="email"
          inputMode="email"
          icon={<Mail className="h-[18px] w-[18px]" />}
          error={errors.email?.message}
          valid={emailLooksValid}
          disabled={busy}
        />

        <PasswordField
          {...register("password")}
          id="login_password"
          label="Password"
          autoComplete="current-password"
          icon={<Lock className="h-[18px] w-[18px]" />}
          error={errors.password?.message}
          disabled={busy}
        />

        {/* Two-factor code — revealed only after the server says this
            account has 2FA enabled, so ordinary logins are unaffected.
            Suppressed while a GOOGLE 2FA challenge is in flight so only
            one code field shows at a time. */}
        <AnimatePresence initial={false}>
          {otpRequired && !pendingOtpToken && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              style={{ overflow: "hidden" }}
            >
              <GatewayField
                {...register("otp_code")}
                id="otp_code"
                label="Authentication code"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={8}
                icon={<ShieldCheck className="h-[18px] w-[18px]" />}
                error={errors.otp_code?.message}
                hint="Open your authenticator app and enter the current code for Sasha Infinity."
                disabled={busy}
                className="tracking-[0.3em]"
                autoFocus
              />
            </motion.div>
          )}
        </AnimatePresence>

        <div className="ag-between">
          <label className="ag-check">
            <input {...register("remember")} type="checkbox" disabled={busy} />
            <span className="ag-check-box" aria-hidden="true">
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round">
                <path d="M3.5 8.5l3 3 6-7" />
              </svg>
            </span>
            Remember me
          </label>
          <Link to="/forgot-password" className="ag-link">
            Forgot password?
          </Link>
        </div>

        <MagneticButton type="submit" disabled={busy} loading={busy} loadingLabel="Signing you in…">
          Sign in
        </MagneticButton>
      </form>

      {/* Google sign-in + 2FA: the backend answered the Google credential
          with the SAME "otp_required" marker the password login uses.
          Submitting re-sends the held Google token with the code to
          /auth/google. Kept OUTSIDE the password form — a nested form would
          be invalid HTML. */}
      <AnimatePresence initial={false}>
        {pendingOtpToken && (
          <motion.form
            onSubmit={onSubmitGoogleOtp}
            className="ag-callout is-teal"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
          >
            <h3>One more step</h3>
            <p className="mb-3">
              Google verified your account. Enter the current code from your authenticator app to finish signing in.
            </p>
            <GatewayField
              id="google_otp_code"
              name="google_otp_code"
              label="Authentication code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={8}
              icon={<ShieldCheck className="h-[18px] w-[18px]" />}
              error={googleOtpError ?? undefined}
              disabled={completingGoogleOtp}
              className="tracking-[0.3em]"
              value={googleOtp}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setGoogleOtp(e.target.value)}
              autoFocus
            />
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button type="submit" className="ag-ghost" disabled={completingGoogleOtp}>
                {completingGoogleOtp ? "Completing…" : "Complete sign-in"}
              </button>
              <button
                type="button"
                onClick={handleCancelGoogleOtp}
                disabled={completingGoogleOtp}
                className="ag-link"
              >
                Use a different method
              </button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>

      <AnimatePresence initial={false}>
        {unverifiedEmail && (
          <motion.div
            className="ag-callout"
            role="status"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
          >
            <h3 className="flex items-center gap-2">
              <MailWarning className="h-4 w-4 text-[#fdba74]" aria-hidden="true" />
              Confirm your email to continue
            </h3>
            <p className="mb-3">
              We sent a verification link to <span className="font-mono text-[#e6ebf3]">{unverifiedEmail}</span>.
              If it never arrived, we can send a fresh one.
            </p>
            <button
              type="button"
              onClick={handleResendVerification}
              disabled={resendingVerification}
              className="ag-ghost"
            >
              {resendingVerification ? "Sending…" : "Resend verification email"}
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="ag-divider">or continue with</div>
      <div className="ag-providers">
        <ProviderCard
          mark={<GoogleMark />}
          name="Google"
          note={isFirebaseConfigured ? "One tap, no password" : "Not available right now"}
          onClick={handleGoogleLogin}
          disabled={busy || isGoogleLoading || !isFirebaseConfigured}
          aria-busy={isGoogleLoading || undefined}
        />
        <ProviderCard
          mark={<LinkedInMark />}
          name="LinkedIn"
          note="Use your professional profile"
          onClick={handleLinkedInLogin}
          disabled={busy}
        />
      </div>

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
