import * as React from "react"
import { Link, useNavigate } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Eye, EyeOff, Mail, Lock, User, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useAuth } from "@/hooks/use-auth"
import { RegisterForm as RegisterFormType } from "@/types"
import { cn } from "@/utils/cn"
import toast from "react-hot-toast"

const registerSchema = z.object({
  first_name: z.string().min(2, "First name must be at least 2 characters"),
  last_name: z.string().min(2, "Last name must be at least 2 characters"),
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(8, "Password must be at least 8 characters")
    .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, "Password must contain at least one uppercase letter, one lowercase letter, and one number"),
  confirm_password: z.string(),
  user_type: z.enum(["student", "instructor"], {
    required_error: "Please select a user type",
  }),
  agree_to_terms: z.boolean().refine(val => val === true, {
    message: "You must agree to the terms and conditions",
  }),
}).refine((data) => data.password === data.confirm_password, {
  message: "Passwords don't match",
  path: ["confirm_password"],
})

export const RegisterForm: React.FC = () => {
  const [showPassword, setShowPassword] = React.useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = React.useState(false)
  const { register: registerUser, isLoading, error, clearError } = useAuth()
  const navigate = useNavigate()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    watch,
    setError,
  } = useForm<RegisterFormType>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      first_name: "",
      last_name: "",
      email: "",
      password: "",
      confirm_password: "",
      user_type: "student",
      agree_to_terms: false,
    },
  })

  const watchedPassword = watch("password")
  const watchedUserType = watch("user_type")

  // Clear errors when component mounts
  React.useEffect(() => {
    clearError()
  }, [clearError])

  // Handle server errors
  React.useEffect(() => {
    if (error) {
      if (error.includes("email")) {
        setError("email", { message: error })
      } else {
        toast.error(error)
      }
    }
  }, [error, setError])

  const onSubmit = async (data: RegisterFormType) => {
    try {
      clearError()
      await registerUser(data)
      toast.success("Account created successfully! Please complete your profile to get started.")
      // Redirect to profile page to complete profile information
      navigate("/profile")
    } catch (err: any) {
      // Error handling is done in the useEffect above
      console.error("Registration error:", err)
      console.error("Error response:", err.response?.data)
      console.error("Error message:", err.message)

      // Show error in toast if not handled by useEffect
      if (err.response?.data?.detail) {
        toast.error(err.response.data.detail)
      }
    }
  }

  const getPasswordStrength = (password: string) => {
    let strength = 0
    if (password.length >= 8) strength++
    if (/[a-z]/.test(password)) strength++
    if (/[A-Z]/.test(password)) strength++
    if (/\d/.test(password)) strength++
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength++
    return strength
  }

  const passwordStrength = getPasswordStrength(watchedPassword)

  const getStrengthLabel = (strength: number) => {
    if (strength < 2) return "Weak"
    if (strength < 4) return "Medium"
    return "Strong"
  }

  const getStrengthColor = (strength: number) => {
    if (strength < 2) return "danger"
    if (strength < 4) return "warning"
    return "success"
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-secondary-50 px-4 sm:px-6 py-8">
      <Card className="w-full max-w-md mx-4">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">Create your account</CardTitle>
          <CardDescription className="text-center">
            Join thousands of learners and start your journey today
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* User Type Selection */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-700">I want to join as</label>
              <div className="grid grid-cols-2 gap-3">
                <label className="relative">
                  <input
                    {...register("user_type")}
                    type="radio"
                    value="student"
                    className="sr-only"
                    disabled={isSubmitting || isLoading}
                  />
                  <div className={cn(
                    "p-4 border rounded-lg cursor-pointer transition-all",
                    watchedUserType === "student"
                      ? "border-primary-500 bg-primary-50 text-primary-700"
                      : "border-neutral-200 hover:border-neutral-300"
                  )}>
                    <div className="text-center">
                      <User className="w-6 h-6 mx-auto mb-2" />
                      <div className="font-medium">Student</div>
                      <div className="text-xs text-neutral-500">Learn from experts</div>
                    </div>
                  </div>
                </label>
                <label className="relative">
                  <input
                    {...register("user_type")}
                    type="radio"
                    value="instructor"
                    className="sr-only"
                    disabled={isSubmitting || isLoading}
                  />
                  <div className={cn(
                    "p-4 border rounded-lg cursor-pointer transition-all",
                    watchedUserType === "instructor"
                      ? "border-primary-500 bg-primary-50 text-primary-700"
                      : "border-neutral-200 hover:border-neutral-300"
                  )}>
                    <div className="text-center">
                      <User className="w-6 h-6 mx-auto mb-2" />
                      <div className="font-medium">Instructor</div>
                      <div className="text-xs text-neutral-500">Teach & earn</div>
                    </div>
                  </div>
                </label>
              </div>
              {errors.user_type && (
                <p className="text-sm text-danger-600">{errors.user_type.message}</p>
              )}
            </div>

            {/* Name Inputs */}
            <div className="grid grid-cols-2 gap-3">
              <Input
                {...register("first_name")}
                placeholder="First name"
                error={errors.first_name?.message}
                disabled={isSubmitting || isLoading}
                className="h-12"
              />
              <Input
                {...register("last_name")}
                placeholder="Last name"
                error={errors.last_name?.message}
                disabled={isSubmitting || isLoading}
                className="h-12"
              />
            </div>

            {/* Email Input */}
            <Input
              {...register("email")}
              type="email"
              placeholder="Enter your email"
              leftIcon={<Mail className="w-4 h-4" />}
              error={errors.email?.message}
              disabled={isSubmitting || isLoading}
              className="h-12"
            />

            {/* Password Input */}
            <div className="space-y-2">
              <div className="relative">
                <Input
                  {...register("password")}
                  type={showPassword ? "text" : "password"}
                  placeholder="Create a password"
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

              {/* Password Strength Indicator */}
              {watchedPassword && (
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-neutral-600">Password strength:</span>
                    <Badge variant={getStrengthColor(passwordStrength)} size="sm">
                      {getStrengthLabel(passwordStrength)}
                    </Badge>
                  </div>
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((level) => (
                      <div
                        key={level}
                        className={cn(
                          "h-1 flex-1 rounded-full",
                          passwordStrength >= level
                            ? passwordStrength < 2
                              ? "bg-danger-500"
                              : passwordStrength < 4
                              ? "bg-warning-500"
                              : "bg-success-500"
                            : "bg-neutral-200"
                        )}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password Input */}
            <div className="relative">
              <Input
                {...register("confirm_password")}
                type={showConfirmPassword ? "text" : "password"}
                placeholder="Confirm your password"
                leftIcon={<Lock className="w-4 h-4" />}
                error={errors.confirm_password?.message}
                disabled={isSubmitting || isLoading}
                className="h-12"
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-neutral-500 hover:text-neutral-700 p-2 min-h-[44px] min-w-[44px] flex items-center justify-center"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                disabled={isSubmitting || isLoading}
              >
                {showConfirmPassword ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>

            {/* Terms and Conditions */}
            <div className="space-y-2">
              <label className="flex items-start space-x-2">
                <input
                  {...register("agree_to_terms")}
                  type="checkbox"
                  className="mt-1 rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
                  disabled={isSubmitting || isLoading}
                />
                <div className="text-sm text-neutral-600">
                  I agree to the{" "}
                  <Link to="/terms" className="text-primary-600 hover:text-primary-700">
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link to="/privacy" className="text-primary-600 hover:text-primary-700">
                    Privacy Policy
                  </Link>
                </div>
              </label>
              {errors.agree_to_terms && (
                <p className="text-sm text-danger-600">{errors.agree_to_terms.message}</p>
              )}
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              className="w-full h-12 sm:h-10"
              disabled={isSubmitting || isLoading}
              loading={isSubmitting || isLoading}
            >
              Create Account
            </Button>
          </form>

          {/* Instructor Benefits */}
          {watchedUserType === "instructor" && (
            <div className="mt-6 p-4 bg-primary-50 rounded-lg">
              <h4 className="font-medium text-primary-900 mb-2">Instructor Benefits</h4>
              <ul className="space-y-1 text-sm text-primary-700">
                <li className="flex items-center">
                  <Check className="w-4 h-4 mr-2" />
                  Earn money from your courses
                </li>
                <li className="flex items-center">
                  <Check className="w-4 h-4 mr-2" />
                  Reach students worldwide
                </li>
                <li className="flex items-center">
                  <Check className="w-4 h-4 mr-2" />
                  Advanced analytics & insights
                </li>
              </ul>
            </div>
          )}

          {/* Sign in link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-neutral-600">
              Already have an account?{" "}
              <Link
                to="/login"
                className="font-medium text-primary-600 hover:text-primary-700"
              >
                Sign in
              </Link>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}