import * as React from "react"
import { X, GraduationCap, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/utils/cn"
import { isValidMobileNumber, normalizeMobileNumber, MOBILE_NUMBER_ERROR } from "@/utils/phone"

export interface RoleSelectionModalProps {
  isOpen: boolean
  onClose: () => void
  onSelect: (role: "student" | "instructor", phone: string) => void
  email?: string
  loading?: boolean
}

export const RoleSelectionModal: React.FC<RoleSelectionModalProps> = ({
  isOpen,
  onClose,
  onSelect,
  email,
  loading = false,
}) => {
  const [selectedRole, setSelectedRole] = React.useState<"student" | "instructor" | null>(null)
  const [phone, setPhone] = React.useState("")
  const [phoneError, setPhoneError] = React.useState<string | null>(null)

  // Reset selection when modal opens/closes
  React.useEffect(() => {
    if (!isOpen) {
      setSelectedRole(null)
      setPhone("")
      setPhoneError(null)
    }
  }, [isOpen])

  // Handle escape key
  React.useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !loading) {
        onClose()
      }
    }

    document.addEventListener("keydown", handleEscape)
    return () => document.removeEventListener("keydown", handleEscape)
  }, [isOpen, onClose, loading])

  // Prevent body scroll when modal is open
  React.useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden"
    } else {
      document.body.style.overflow = ""
    }

    return () => {
      document.body.style.overflow = ""
    }
  }, [isOpen])

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !loading) {
      onClose()
    }
  }

  const handleRoleSelect = (role: "student" | "instructor") => {
    setSelectedRole(role)
  }

  const handleContinue = () => {
    if (!selectedRole) return

    // Google gives us no phone number, so it is collected here and is
    // mandatory — the account is only created once we have a valid one.
    if (!isValidMobileNumber(phone)) {
      setPhoneError(MOBILE_NUMBER_ERROR)
      return
    }

    setPhoneError(null)
    onSelect(selectedRole, normalizeMobileNumber(phone))
  }

  if (!isOpen) return null

  const roleCards = [
    {
      id: "student" as const,
      icon: GraduationCap,
      title: "Student",
      description: "Learn from experts",
    },
    {
      id: "instructor" as const,
      icon: Sparkles,
      title: "Instructor",
      description: "Teach & earn",
    },
  ]

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={handleBackdropClick}
      aria-labelledby="modal-title"
      role="dialog"
      aria-modal="true"
    >
      <div
        className={cn(
          "relative w-full max-w-lg bg-white rounded-2xl shadow-2xl transition-all",
          "animate-in fade-in-0 zoom-in-95 duration-200"
        )}
      >
        {/* Close button */}
        {!loading && (
          <button
            onClick={onClose}
            className="absolute right-4 top-4 rounded-full p-2 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        )}

        {/* Content */}
        <div className="p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <h2
              id="modal-title"
              className="text-2xl font-bold text-neutral-900 mb-2"
            >
              Create your account
            </h2>
            <p className="text-neutral-600">
              Join thousands of learners and start your journey today
            </p>
            {email && (
              <p className="text-sm text-neutral-500 mt-2">
                Signing in as <span className="font-medium">{email}</span>
              </p>
            )}
          </div>

          {/* Role prompt */}
          <p className="text-center font-medium text-neutral-800 mb-6">
            I want to join as:
          </p>

          {/* Role cards */}
          <div className="grid grid-cols-2 gap-4 mb-8">
            {roleCards.map((role) => {
              const Icon = role.icon
              const isSelected = selectedRole === role.id

              return (
                <button
                  key={role.id}
                  onClick={() => handleRoleSelect(role.id)}
                  disabled={loading}
                  className={cn(
                    "relative flex flex-col items-center justify-center p-6 rounded-xl border-2 transition-all duration-200",
                    "min-h-[160px]",
                    isSelected
                      ? "border-primary-500 bg-primary-50 shadow-md"
                      : "border-neutral-200 bg-white hover:border-primary-300 hover:shadow-sm",
                    loading && "cursor-not-allowed opacity-60"
                  )}
                >
                  {isSelected && (
                    <div className="absolute top-3 right-3 w-5 h-5 rounded-full bg-primary-500 flex items-center justify-center">
                      <svg
                        className="w-3 h-3 text-white"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </div>
                  )}

                  <div
                    className={cn(
                      "w-12 h-12 rounded-full flex items-center justify-center mb-3",
                      isSelected
                        ? "bg-primary-500 text-white"
                        : "bg-neutral-100 text-neutral-600"
                    )}
                  >
                    <Icon className="w-6 h-6" />
                  </div>

                  <h3 className="font-semibold text-neutral-900 mb-1">
                    {role.title}
                  </h3>

                  <p className="text-sm text-neutral-600">{role.description}</p>
                </button>
              )
            })}
          </div>

          {/* Mobile number — mandatory, Google never provides one */}
          <div className="mb-8">
            <label
              htmlFor="google-signup-phone"
              className="block text-sm font-medium text-neutral-800 mb-2"
            >
              Mobile number <span className="text-red-500">*</span>
            </label>
            <div className="flex items-stretch">
              <span className="inline-flex items-center px-3 rounded-l-lg border border-r-0 border-neutral-300 bg-neutral-50 text-neutral-600 text-sm">
                +91
              </span>
              <input
                id="google-signup-phone"
                type="tel"
                inputMode="numeric"
                autoComplete="tel"
                maxLength={10}
                value={phone}
                disabled={loading}
                onChange={(e) => {
                  setPhone(e.target.value.replace(/\D/g, "").slice(0, 10))
                  if (phoneError) setPhoneError(null)
                }}
                placeholder="9876543210"
                aria-invalid={!!phoneError}
                aria-describedby={phoneError ? "google-signup-phone-error" : undefined}
                className={cn(
                  "flex-1 min-w-0 rounded-r-lg border px-3 py-2 text-neutral-900 outline-none transition-colors",
                  "focus:border-primary-500 focus:ring-2 focus:ring-primary-100",
                  phoneError ? "border-red-400" : "border-neutral-300",
                  loading && "bg-neutral-50 cursor-not-allowed"
                )}
              />
            </div>
            {phoneError ? (
              <p id="google-signup-phone-error" className="mt-2 text-sm text-red-600">
                {phoneError}
              </p>
            ) : (
              <p className="mt-2 text-xs text-neutral-500">
                We use this to reach you about your courses. Required to continue.
              </p>
            )}
          </div>

          {/* Continue button */}
          <Button
            onClick={handleContinue}
            disabled={!selectedRole || !isValidMobileNumber(phone) || loading}
            loading={loading}
            className="w-full"
            size="lg"
          >
            {loading ? "Creating account..." : "Continue"}
          </Button>
        </div>
      </div>
    </div>
  )
}
