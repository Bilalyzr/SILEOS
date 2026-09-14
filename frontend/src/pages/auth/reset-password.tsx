import * as React from "react"
import { Link, useSearchParams, useNavigate } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Eye, EyeOff, Lock, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { authAPI } from "@/api/auth"
import toast from "react-hot-toast"

const resetPasswordSchema = z.object({
  password: z.string().min(8, "Password must be at least 8 characters")
    .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, "Password must contain at least one uppercase letter, one lowercase letter, and one number"),
  confirm_password: z.string(),
}).refine((data) => data.password === data.confirm_password, {
  message: "Passwords don't match",
  path: ["confirm_password"],
})

type ResetPasswordForm = z.infer<typeof resetPasswordSchema>

export const ResetPasswordPage = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [showPassword, setShowPassword] = React.useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = React.useState(false)

  const token = searchParams.get('token')

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordForm>({
    resolver: zodResolver(resetPasswordSchema),
  })

  // Redirect if no token
  React.useEffect(() => {
    if (!token) {
      navigate('/forgot-password')
    }
  }, [token, navigate])

  const onSubmit = async (data: ResetPasswordForm) => {
    if (!token) return

    try {
      await authAPI.resetPassword(token, data.password)
      toast.success("Password reset successfully! You can now sign in with your new password.")
      navigate('/login')
    } catch (error: any) {
      toast.error(error.message || "Failed to reset password")
    }
  }

  if (!token) {
    return null
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold text-center">Reset Password</CardTitle>
        <CardDescription className="text-center">
          Enter your new password below
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* New Password */}
          <div className="relative">
            <Input
              {...register("password")}
              type={showPassword ? "text" : "password"}
              placeholder="Enter new password"
              leftIcon={<Lock className="w-4 h-4" />}
              error={errors.password?.message}
              disabled={isSubmitting}
            />
            <button
              type="button"
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-neutral-500 hover:text-neutral-700"
              onClick={() => setShowPassword(!showPassword)}
              disabled={isSubmitting}
            >
              {showPassword ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>

          {/* Confirm Password */}
          <div className="relative">
            <Input
              {...register("confirm_password")}
              type={showConfirmPassword ? "text" : "password"}
              placeholder="Confirm new password"
              leftIcon={<Lock className="w-4 h-4" />}
              error={errors.confirm_password?.message}
              disabled={isSubmitting}
            />
            <button
              type="button"
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-neutral-500 hover:text-neutral-700"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              disabled={isSubmitting}
            >
              {showConfirmPassword ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={isSubmitting}
            loading={isSubmitting}
          >
            Reset Password
          </Button>
        </form>

        <div className="mt-6 text-center">
          <Link
            to="/login"
            className="inline-flex items-center text-primary-600 hover:text-primary-700 text-sm font-medium"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Sign In
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}