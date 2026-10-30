import * as React from "react"
import { Link, useSearchParams, useNavigate } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Lock, ArrowLeft } from "lucide-react"
import { MagneticButton, PasswordField } from "@/components/auth/gateway/GatewayControls"
import { authAPI } from "@/api/auth"
import toast from "react-hot-toast"

const resetPasswordSchema = z.object({
  password: z.string().min(8, "Use at least 8 characters.")
    .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, "Add an uppercase letter, a lowercase letter and a number."),
  confirm_password: z.string(),
}).refine((data) => data.password === data.confirm_password, {
  message: "These passwords don't match yet.",
  path: ["confirm_password"],
})

type ResetPasswordForm = z.infer<typeof resetPasswordSchema>

export const ResetPasswordPage = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

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
    <div className="w-full">
      <div className="ag-head">
        <h2>Choose a new password</h2>
        <p>Make it something you haven't used here before.</p>
      </div>
      <form onSubmit={handleSubmit(onSubmit)} className="ag-form" noValidate>
        <PasswordField
          {...register("password")}
          id="reset_password"
          label="New password"
          autoComplete="new-password"
          icon={<Lock className="h-[18px] w-[18px]" />}
          error={errors.password?.message}
          disabled={isSubmitting}
          meter
        />
        <PasswordField
          {...register("confirm_password")}
          id="reset_confirm_password"
          label="Confirm new password"
          autoComplete="new-password"
          icon={<Lock className="h-[18px] w-[18px]" />}
          error={errors.confirm_password?.message}
          disabled={isSubmitting}
        />
        <MagneticButton type="submit" disabled={isSubmitting} loading={isSubmitting} loadingLabel="Saving…">
          Save new password
        </MagneticButton>
      </form>
      <div className="ag-foot">
        <Link to="/login" className="ag-link gap-1.5">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to sign in
        </Link>
      </div>
    </div>
  )
}
