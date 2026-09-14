import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { User, GraduationCap, Loader2, CheckCircle } from 'lucide-react'
import { cn } from '@/utils/cn'
import { api } from '@/api/axios'
import toast from 'react-hot-toast'
import { useGoogleOAuth } from '@/hooks/use-google-oauth'
import { RoleSelectionModal } from '@/components/auth/RoleSelectionModal'
import { isFirebaseConfigured } from '@/lib/firebase'

export const UnifiedRegisterForm = () => {
  const navigate = useNavigate()
  const [userType, setUserType] = useState<'student' | 'instructor'>('student')
  const [loading, setLoading] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  const { signInWithGoogle, isLoading: isGoogleLoading, pendingGoogleUser } = useGoogleOAuth()
  const [completingGoogleAuth, setCompletingGoogleAuth] = useState(false)
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
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validation
    if (formData.password !== formData.confirmPassword) {
      toast.error('Passwords do not match')
      return
    }

    if (!formData.agreeToTerms) {
      toast.error('Please agree to the Terms of Service and Privacy Policy')
      return
    }

    if (userType === 'instructor' && (!formData.designation || !formData.bio)) {
      toast.error('Please fill in your designation and bio')
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
      toast.error(message)
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
      <Card className="w-full max-w-md">
        <CardContent className="pt-6">
          <div className="text-center space-y-4">
            <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle className="w-10 h-10 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Registration Successful!</h2>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-900">
                📧 <strong>Check your email!</strong>
              </p>
              <p className="text-sm text-blue-800 mt-2">
                We've sent a verification link to <strong>{formData.email}</strong>
              </p>
              <p className="text-xs text-blue-700 mt-2">
                Please verify your email address to complete registration.
              </p>
            </div>
            {userType === 'instructor' && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-sm text-yellow-900">
                  ⏳ <strong>Pending Approval</strong>
                </p>
                <p className="text-xs text-yellow-800 mt-1">
                  Your instructor account will be reviewed by our admin team.
                </p>
              </div>
            )}
            <p className="text-sm text-gray-600">
              Redirecting to login page...
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <CardTitle className="text-3xl font-bold">Create your account</CardTitle>
        <CardDescription>Join thousands of learners and start your journey today</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* User Type Selection */}
          <div>
            <label className="text-sm font-medium mb-3 block">I want to join as</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setUserType('student')}
                className={cn(
                  "p-4 border-2 rounded-lg transition-all text-left",
                  userType === 'student'
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-gray-300"
                )}
              >
                <User className={cn("w-6 h-6 mb-2", userType === 'student' ? "text-blue-600" : "text-gray-400")} />
                <div className="font-semibold text-sm">Student</div>
                <div className="text-xs text-gray-600">Learn from experts</div>
              </button>

              <button
                type="button"
                onClick={() => setUserType('instructor')}
                className={cn(
                  "p-4 border-2 rounded-lg transition-all text-left",
                  userType === 'instructor'
                    ? "border-purple-500 bg-purple-50"
                    : "border-gray-200 hover:border-gray-300"
                )}
              >
                <GraduationCap className={cn("w-6 h-6 mb-2", userType === 'instructor' ? "text-purple-600" : "text-gray-400")} />
                <div className="font-semibold text-sm">Instructor</div>
                <div className="text-xs text-gray-600">Teach & earn</div>
              </button>
            </div>
          </div>

          {/* Name Fields */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="firstName" className="text-sm font-medium block mb-1">First name</label>
              <Input
                id="firstName"
                name="firstName"
                type="text"
                required
                value={formData.firstName}
                onChange={handleChange}
                placeholder="John"
              />
            </div>
            <div>
              <label htmlFor="lastName" className="text-sm font-medium block mb-1">Last name</label>
              <Input
                id="lastName"
                name="lastName"
                type="text"
                required
                value={formData.lastName}
                onChange={handleChange}
                placeholder="Doe"
              />
            </div>
          </div>

          {/* Email */}
          <div>
            <label htmlFor="email" className="text-sm font-medium block mb-1">Email</label>
            <Input
              id="email"
              name="email"
              type="email"
              required
              value={formData.email}
              onChange={handleChange}
              placeholder="Enter your email"
            />
          </div>

          {/* Instructor-specific fields */}
          {userType === 'instructor' && (
            <>
              <div>
                <label htmlFor="designation" className="text-sm font-medium block mb-1">Designation *</label>
                <Input
                  id="designation"
                  name="designation"
                  type="text"
                  required
                  value={formData.designation}
                  onChange={handleChange}
                  placeholder="e.g., Senior Software Engineer"
                />
              </div>

              <div>
                <label htmlFor="bio" className="text-sm font-medium block mb-1">Bio *</label>
                <textarea
                  id="bio"
                  name="bio"
                  required
                  rows={3}
                  value={formData.bio}
                  onChange={handleChange}
                  placeholder="Tell us about yourself and your teaching experience..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </>
          )}

          {/* Password Fields */}
          <div>
            <label htmlFor="password" className="text-sm font-medium block mb-1">Create a password</label>
            <Input
              id="password"
              name="password"
              type="password"
              required
              value={formData.password}
              onChange={handleChange}
              placeholder="••••••••"
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="text-sm font-medium block mb-1">Confirm your password</label>
            <Input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              required
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="••••••••"
            />
          </div>

          {/* Terms and Conditions */}
          <div className="flex items-start space-x-2">
            <input
              type="checkbox"
              id="terms"
              checked={formData.agreeToTerms}
              onChange={(e) => setFormData({ ...formData, agreeToTerms: e.target.checked })}
              className="mt-1"
            />
            <label htmlFor="terms" className="text-sm text-gray-600 leading-tight">
              I agree to the <Link to="/terms" className="text-blue-600 hover:underline">Terms of Service</Link> and{' '}
              <Link to="/privacy" className="text-blue-600 hover:underline">Privacy Policy</Link>
            </label>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating Account...
              </>
            ) : (
              'Create Account'
            )}
          </Button>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
          </div>

          {/* Social Login Buttons */}
          <div className="space-y-3">
            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={handleGoogleSignUp}
              disabled={loading || isGoogleLoading || !isFirebaseConfigured}
            >
              <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24">
                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
              Continue with Google
            </Button>
          </div>

          {/* Login Link */}
          <p className="text-center text-sm text-gray-600">
            Already have an account?{' '}
            <Link to="/login" className="text-blue-600 hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  )
}
