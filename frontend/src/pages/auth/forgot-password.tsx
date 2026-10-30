import * as React from "react"
import { Link } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { motion } from "framer-motion"
import { Mail, ArrowLeft, MailCheck } from "lucide-react"
import { GatewayField } from "@/components/auth/gateway/GatewayField"
import { MagneticButton } from "@/components/auth/gateway/GatewayControls"
import { authAPI } from "@/api/auth"
import toast from "react-hot-toast"

const forgotPasswordSchema = z.object({
  email: z.string().email("Enter the email you signed up with, like name@example.com."),
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
      <motion.div
        className="w-full py-1 text-center"
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        role="status"
      >
        <motion.div
          className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-[rgba(45,212,191,0.12)] text-[#2dd4bf] shadow-[0_0_0_1px_rgba(45,212,191,0.3)_inset,0_0_40px_rgba(45,212,191,0.25)]"
          initial={{ rotate: -12, scale: 0.6 }}
          animate={{ rotate: 0, scale: 1 }}
          transition={{ type: "spring", stiffness: 300, damping: 16 }}
        >
          <MailCheck className="h-8 w-8" aria-hidden="true" />
        </motion.div>
        <div className="ag-head mt-5">
          <h2>Check your inbox</h2>
          <p>
            If an account exists for <strong className="text-white">{email}</strong>, a reset link is on its way.
          </p>
        </div>
        <p className="ag-foot">Nothing yet? Check spam, or send it again.</p>
        <div className="mt-3 flex flex-wrap items-center justify-center gap-3">
          <button type="button" className="ag-ghost" onClick={() => setIsSubmitted(false)}>
            Try again
          </button>
          <Link to="/login" className="ag-link gap-1.5">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to sign in
          </Link>
        </div>
      </motion.div>
    )
  }

  return (
    <div className="w-full">
      <div className="ag-head">
        <h2>Reset your password</h2>
        <p>Enter your email and we'll send you a secure link to choose a new one.</p>
      </div>
      <form onSubmit={handleSubmit(onSubmit)} className="ag-form" noValidate>
        <GatewayField
          {...register("email")}
          id="forgot_email"
          label="Email address"
          type="email"
          autoComplete="email"
          inputMode="email"
          icon={<Mail className="h-[18px] w-[18px]" />}
          error={errors.email?.message}
          disabled={isSubmitting}
        />
        <MagneticButton type="submit" disabled={isSubmitting} loading={isSubmitting} loadingLabel="Sending link…">
          Send reset link
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
