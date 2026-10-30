import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { User, GraduationCap, Mail, Lock, Briefcase, MailCheck, Hourglass } from 'lucide-react'
import { api } from '@/api/axios'
import toast from 'react-hot-toast'
import { useGoogleOAuth } from '@/hooks/use-google-oauth'
import { RoleSelectionModal } from '@/components/auth/RoleSelectionModal'
import { isFirebaseConfigured } from '@/lib/firebase'
import { GatewayField } from '@/components/auth/gateway/GatewayField'
import { GoogleMark, MagneticButton, PasswordField, ProviderCard } from '@/components/auth/gateway/GatewayControls'
import { useGateway } from '@/components/auth/gateway/GatewayContext'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/

type FieldErrors = Partial<Record<'firstName' | 'lastName' | 'email' | 'password' | 'confirmPassword' | 'designation' | 'bio' | 'agreeToTerms', string>>

const ROLES = [
  { id: 'student' as const, title: 'Student', note: 'Learn from experts', Icon: User },
  { id: 'instructor' as const, title: 'Instructor', note: 'Teach and earn', Icon: GraduationCap },
]

export const UnifiedRegisterForm = () => {
  const navigate = useNavigate()
  const { reportFocus } = useGateway()
  const [userType, setUserType] = useState<'student' | 'instructor'>('student')
  const [loading, setLoading] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  const { signInWithGoogle, isLoading: isGoogleLoading, pendingGoogleUser } = useGoogleOAuth()
  const [completingGoogleAuth, setCompletingGoogleAuth] = useState(false)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    confirmPassword: '',
    designation: '',
    bio: '',
    agreeToTerms: false
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const name = e.target.name as keyof FieldErrors
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
    // Guidance clears as soon as the visitor starts fixing the field
    if (errors[name]) setErrors({ ...errors, [name]: undefined })
  }

  const validate = (): FieldErrors => {
    const next: FieldErrors = {}
    if (!formData.firstName.trim()) next.firstName = 'Add your first name.'
    if (!formData.lastName.trim()) next.lastName = 'Add your last name.'
    if (!EMAIL_RE.test(formData.email)) next.email = 'Enter an email you can open, like name@example.com.'
    if (formData.password.length < 8) next.password = 'Use at least 8 characters.'
    if (formData.password !== formData.confirmPassword) next.confirmPassword = "These passwords don't match yet."
    if (userType === 'instructor') {
      if (!formData.designation.trim()) next.designation = 'Tell learners your current role.'
      if (!formData.bio.trim()) next.bio = 'A short bio helps our team review your application.'
    }
    if (!formData.agreeToTerms) next.agreeToTerms = 'Please accept the Terms and Privacy Policy to continue.'
    return next
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const found = validate()
    setErrors(found)
    if (Object.keys(found).length > 0) {
      // Take the visitor straight to the first thing to fix
      const first = Object.keys(found)[0]
      const el = document.getElementById(first === 'agreeToTerms' ? 'terms' : first)
      el?.focus()
      return
    }

    try {
      setLoading(true)

      const payload = {
        first_name: formData.firstName,
        last_name: formData.lastName,
        email: formData.email,
        password: formData.password,
        user_type: userType,
        ...(userType === 'instructor' && {
          designation: formData.designation,
          bio: formData.bio
        })
      }

      await api.post(`/auth/register`, payload)

      setShowSuccess(true)

      toast.success(
        userType === 'instructor'
          ? 'Registration successful! Please check your email to verify your account. Your instructor account is pending admin approval.'
          : 'Registration successful! Please check your email to verify your account.',
        { duration: 7000 }
      )

      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate('/login')
      }, 3000)

    } catch (error: any) {
      console.error('Registration error:', error)
      // FastAPI 422 validation errors return `detail` as an array of
      // {loc, msg, type} objects — stringifying it directly shows
      // "[object Object]". Flatten to the human-readable messages.
      const detail = error.response?.data?.detail
      let message = 'Registration failed. Please try again.'
      if (typeof detail === 'string') {
        message = detail
      } else if (Array.isArray(detail)) {
        message = detail
          .map((d: any) => d?.msg || d?.message || '')
          .filter(Boolean)
          .join(', ') || message
      }
      // An address that is already registered is a field problem with a
      // clear recovery path, not a generic failure.
      if (/already|exists|registered/i.test(message) && /email/i.test(message)) {
        setErrors({ email: 'This email already has an account. Sign in instead, or reset your password.' })
      } else {
        toast.error(message)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleSignUp = async () => {
    try {
      const result = await signInWithGoogle()
      // An EXISTING TOTP-enrolled account hitting Google sign-up gets the
      // backend's 2FA challenge; the OTP UI lives on the login screen.
      if (result && 'otpRequired' in result) {
        toast.error('This account uses two-factor authentication. Sign in from the login page to enter your code.', { duration: 6000 })
        return
      }
      // If pendingGoogleUser is set, the modal will open automatically
    } catch (err: any) {
      console.error("Google sign-up error:", err)
    }
  }

  const handleRoleSelect = async (role: 'student' | 'instructor', phone: string) => {
    if (!pendingGoogleUser) return

    setCompletingGoogleAuth(true)

    try {
      const { authAPI } = await import('@/api/auth')
      await authAPI.completeGoogleSignIn({
        email: pendingGoogleUser.email,
        role: role,
        googleToken: pendingGoogleUser.token,
        phone
      })

      // Show success message
      setShowSuccess(true)

      // Redirect to login after delay
      setTimeout(() => {
        navigate('/login', { state: { message: 'Account created successfully! Please sign in.' } })
      }, 3000)
    } catch (err: any) {
      console.error('Complete Google auth error:', err)
      toast.error(err.response?.data?.detail || 'Failed to complete sign up. Please try again.')
    } finally {
      setCompletingGoogleAuth(false)
    }
  }

  // Show role modal when pending Google user exists
  if (pendingGoogleUser) {
    return (
      <RoleSelectionModal
        isOpen={true}
        onClose={() => {}}
        onSelect={handleRoleSelect}
        email={pendingGoogleUser.email}
        loading={completingGoogleAuth}
      />
    )
  }

  if (showSuccess) {
    return (
      <motion.div
        className="w-full py-2 text-center"
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        role="status"
      >
        <motion.div
          className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-[rgba(45,212,191,0.12)] text-[#2dd4bf] shadow-[0_0_0_1px_rgba(45,212,191,0.3)_inset,0_0_40px_rgba(45,212,191,0.25)]"
          initial={{ rotate: -12, scale: 0.6 }}
          animate={{ rotate: 0, scale: 1 }}
          transition={{ type: 'spring', stiffness: 300, damping: 16, delay: 0.1 }}
        >
          <MailCheck className="h-8 w-8" aria-hidden="true" />
        </motion.div>
        <div className="ag-head mt-5">
          <h2>You're in. Check your inbox.</h2>
          <p>
            We sent a verification link to <strong className="text-white">{formData.email || 'your email'}</strong>.
            Open it to activate your account.
          </p>
        </div>
        {userType === 'instructor' && (
          <div className="ag-callout text-left">
            <h3 className="flex items-center gap-2">
              <Hourglass className="h-4 w-4 text-[#fdba74]" aria-hidden="true" />
              Instructor review
            </h3>
            <p>Our team reviews every instructor account before it goes live. We'll email you once it's approved.</p>
          </div>
        )}
        <p className="ag-foot">Taking you to sign in…</p>
      </motion.div>
    )
  }

  return (
    <div className="w-full">
      <div className="ag-head">
        <h2>Create your account</h2>
        <p>Free to join. Choose how you'll use Sasha Infinity.</p>
      </div>

      <form onSubmit={handleSubmit} className="ag-form" noValidate>
        <div className="ag-roles" role="radiogroup" aria-label="I want to join as">
          {ROLES.map(({ id, title, note, Icon }) => {
            const active = userType === id
            return (
              <button
                key={id}
                type="button"
                role="radio"
                aria-checked={active}
                className="ag-role"
                onClick={() => setUserType(id)}
                onFocus={() => reportFocus(`role-${id}`, true)}
                onBlur={() => reportFocus(`role-${id}`, false)}
              >
                {active && (
                  <motion.span
                    layoutId="ag-role-active"
                    className="ag-role-active"
                    transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                  />
                )}
                <span className="ag-role-icon" aria-hidden="true">
                  <Icon className="h-[18px] w-[18px]" />
                </span>
                <span className="ag-role-text">
                  <b>{title}</b>
                  <small>{note}</small>
                </span>
              </button>
            )
          })}
        </div>

        <div className="ag-row-2">
          <GatewayField
            id="firstName"
            name="firstName"
            label="First name"
            autoComplete="given-name"
            value={formData.firstName}
            onChange={handleChange}
            error={errors.firstName}
            valid={formData.firstName.trim().length > 0}
          />
          <GatewayField
            id="lastName"
            name="lastName"
            label="Last name"
            autoComplete="family-name"
            value={formData.lastName}
            onChange={handleChange}
            error={errors.lastName}
            valid={formData.lastName.trim().length > 0}
          />
        </div>

        <GatewayField
          id="email"
          name="email"
          type="email"
          label="Email address"
          autoComplete="email"
          inputMode="email"
          icon={<Mail className="h-[18px] w-[18px]" />}
          value={formData.email}
          onChange={handleChange}
          error={errors.email}
          valid={EMAIL_RE.test(formData.email)}
        />

        {/* Instructor-specific fields glide in when Instructor is chosen */}
        <AnimatePresence initial={false}>
          {userType === 'instructor' && (
            <motion.div
              key="instructor"
              className="grid gap-[14px]"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3, ease: [0.2, 0.7, 0.3, 1] }}
              style={{ overflow: 'hidden' }}
            >
              <GatewayField
                id="designation"
                name="designation"
                label="Your role, e.g. Senior Software Engineer"
                autoComplete="organization-title"
                icon={<Briefcase className="h-[18px] w-[18px]" />}
                value={formData.designation}
                onChange={handleChange}
                error={errors.designation}
                valid={formData.designation.trim().length > 0}
              />
              <div className="ag-field-block">
                <div className="ag-textarea">
                  <label htmlFor="bio">About you and your teaching</label>
                  <textarea
                    id="bio"
                    name="bio"
                    rows={3}
                    value={formData.bio}
                    onChange={handleChange}
                    onFocus={() => reportFocus('bio', true)}
                    onBlur={() => reportFocus('bio', false)}
                    aria-invalid={errors.bio ? true : undefined}
                    aria-describedby={errors.bio ? 'bio-msg' : undefined}
                    placeholder="What you teach, where you've worked, what learners will gain."
                  />
                </div>
                {errors.bio && (
                  <p id="bio-msg" className="ag-field-msg is-error" role="alert">
                    {errors.bio}
                  </p>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <PasswordField
          id="password"
          name="password"
          label="Create a password"
          autoComplete="new-password"
          icon={<Lock className="h-[18px] w-[18px]" />}
          value={formData.password}
          onChange={handleChange}
          error={errors.password}
          meter
        />

        <PasswordField
          id="confirmPassword"
          name="confirmPassword"
          label="Confirm password"
          autoComplete="new-password"
          icon={<Lock className="h-[18px] w-[18px]" />}
          value={formData.confirmPassword}
          onChange={handleChange}
          error={errors.confirmPassword}
          valid={formData.confirmPassword.length > 0 && formData.confirmPassword === formData.password}
          hint={
            formData.confirmPassword && formData.confirmPassword !== formData.password
              ? "Keep typing — this doesn't match yet."
              : undefined
          }
        />

        <div className="ag-field-block">
          <label className="ag-check items-start py-1">
            <input
              type="checkbox"
              id="terms"
              checked={formData.agreeToTerms}
              onChange={(e) => {
                setFormData({ ...formData, agreeToTerms: e.target.checked })
                if (errors.agreeToTerms) setErrors({ ...errors, agreeToTerms: undefined })
              }}
              aria-invalid={errors.agreeToTerms ? true : undefined}
              aria-describedby={errors.agreeToTerms ? 'terms-msg' : undefined}
            />
            <span className="ag-check-box mt-0.5" aria-hidden="true">
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round">
                <path d="M3.5 8.5l3 3 6-7" />
              </svg>
            </span>
            <span className="leading-snug">
              I agree to the <Link to="/terms">Terms of Service</Link> and <Link to="/privacy">Privacy Policy</Link>
            </span>
          </label>
          {errors.agreeToTerms && (
            <p id="terms-msg" className="ag-field-msg is-error" role="alert">
              {errors.agreeToTerms}
            </p>
          )}
        </div>

        <MagneticButton type="submit" disabled={loading} loading={loading} loadingLabel="Creating your account…">
          Create account
        </MagneticButton>
      </form>

      <div className="ag-divider">or sign up with</div>
      <div className="ag-providers is-single">
        <ProviderCard
          mark={<GoogleMark />}
          name="Google"
          note={isFirebaseConfigured ? "We'll ask whether you're a student or instructor" : 'Not available right now'}
          onClick={handleGoogleSignUp}
          disabled={loading || isGoogleLoading || !isFirebaseConfigured}
          aria-busy={isGoogleLoading || undefined}
        />
      </div>
    </div>
  )
}
