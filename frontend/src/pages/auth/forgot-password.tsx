import * as React from "react"
import { Link } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Mail, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { authAPI } from "@/api/auth"
import toast from "react-hot-toast"

const forgotPasswordSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
})

type ForgotPasswordForm = z.infer<typeof forgotPasswordSchema>

export const ForgotPasswordPage = () => {
  const [isSubmitted, setIsSubmitted] = React.useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    watch,
  } = useForm<ForgotPasswordForm>({
    resolver: zodResolver(forgotPasswordSchema),
  })

  const email = watch("email")

  const onSubmit = async (data: ForgotPasswordForm) => {
    try {
      await authAPI.forgotPassword(data.email)
      setIsSubmitted(true)
      toast.success("Password reset instructions sent to your email")
    } catch (error: any) {
      toast.error(error.message || "Failed to send reset instructions")
    }
  }

  if (isSubmitted) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-success-100 rounded-full flex items-center justify-center">
            <Mail className="w-8 h-8 text-success-600" />
          </div>
          <CardTitle className="text-2xl font-bold">Check Your Email</CardTitle>
          <CardDescription>
            We've sent password reset instructions to {email}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-center space-y-4">
            <p className="text-sm text-neutral-600">
              Didn't receive the email? Check your spam folder or
            </p>
            <Button
              variant="outline"
              onClick={() => setIsSubmitted(false)}
              className="w-full"
            >
              Try Again
            </Button>
          </div>
          <div className="text-center">
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

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold text-center">Forgot Password?</CardTitle>
        <CardDescription className="text-center">
          Enter your email address and we'll send you instructions to reset your password
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            {...register("email")}
            type="email"
            placeholder="Enter your email address"
            leftIcon={<Mail className="w-4 h-4" />}
            error={errors.email?.message}
            disabled={isSubmitting}
          />

          <Button
            type="submit"
            className="w-full"
            disabled={isSubmitting}
            loading={isSubmitting}
          >
            Send Reset Instructions
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