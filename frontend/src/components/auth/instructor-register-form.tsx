import * as React from "react"
import { useNavigate } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Eye, EyeOff, Mail, Lock, User, Check, ArrowRight, ArrowLeft, Phone, Briefcase } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/hooks/use-auth"
import { api } from "@/api/axios"
import toast from "react-hot-toast"

const instructorRegisterSchema = z.object({
  first_name: z.string().min(2, "First name must be at least 2 characters"),
  last_name: z.string().min(2, "Last name must be at least 2 characters"),
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(8, "Password must be at least 8 characters")
    .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, "Password must contain at least one uppercase letter, one lowercase letter, and one number"),
  confirm_password: z.string(),
  phone: z.string().min(10, "Phone number must be at least 10 digits"),
  designation: z.string().min(2, "Designation is required"),
  bio: z.string().min(50, "Bio must be at least 50 characters"),
  experience: z.string().min(10, "Please describe your experience"),
  user_type: z.literal("instructor"),
  agree_to_terms: z.boolean().refine(val => val === true, {
    message: "You must agree to the terms and conditions",
  }),
}).refine((data) => data.password === data.confirm_password, {
  message: "Passwords don't match",
  path: ["confirm_password"],
})

type InstructorRegisterForm = z.infer<typeof instructorRegisterSchema>

export const InstructorRegisterForm: React.FC = () => {
  const [currentStep, setCurrentStep] = React.useState(1)
  const [showPassword, setShowPassword] = React.useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = React.useState(false)
  const [emailCheckLoading, setEmailCheckLoading] = React.useState(false)
  const [emailExists, setEmailExists] = React.useState(false)
  const { isLoading, error, clearError } = useAuth()
  const navigate = useNavigate()

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    trigger,
  } = useForm<InstructorRegisterForm>({
    resolver: zodResolver(instructorRegisterSchema),
    mode: "onChange",
    defaultValues: {
      first_name: "",
      last_name: "",
      email: "",
      password: "",
      confirm_password: "",
      phone: "",
      designation: "",
      bio: "",
      experience: "",
      user_type: "instructor",
      agree_to_terms: false,
    },
  })

  const watchedFields = watch()

  React.useEffect(() => {
    clearError()
  }, [clearError])

  React.useEffect(() => {
    if (error) {
      toast.error(error)
    }
  }, [error])

  // Check email availability
  const checkEmailAvailability = React.useCallback(async (email: string) => {
    if (!email || !email.includes('@')) return

    setEmailCheckLoading(true)
    try {
      const response = await api.get(`/auth/check-email?email=${encodeURIComponent(email)}`)
      const data = response.data
      setEmailExists(data.exists)
      if (data.exists) {
        toast.error("This email is already registered. Please use a different email or login.")
      }
    } catch (err) {
      console.error("Error checking email:", err)
    } finally {
      setEmailCheckLoading(false)
    }
  }, [])

  // Debounced email check
  React.useEffect(() => {
    const email = watchedFields.email
    if (!email) return

    const timeoutId = setTimeout(() => {
      checkEmailAvailability(email)
    }, 500)

    return () => clearTimeout(timeoutId)
  }, [watchedFields.email, checkEmailAvailability])

  const validateStep = async (step: number) => {
    let fieldsToValidate: (keyof InstructorRegisterForm)[] = []

    switch (step) {
      case 1:
        fieldsToValidate = ["first_name", "last_name", "email", "phone"]
        break
      case 2:
        fieldsToValidate = ["password", "confirm_password"]
        break
      case 3:
        fieldsToValidate = ["designation", "bio", "experience"]
        break
      case 4:
        fieldsToValidate = ["agree_to_terms"]
        break
    }

    const result = await trigger(fieldsToValidate)
    return result
  }

  const nextStep = async () => {
    // Check if email exists before moving forward from step 1
    if (currentStep === 1 && emailExists) {
      toast.error("Please use a different email address")
      return
    }

    const isStepValid = await validateStep(currentStep)
    if (isStepValid) {
      setCurrentStep((prev) => Math.min(prev + 1, 4))
    }
  }

  const prevStep = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 1))
  }

  const onSubmit = async (data: InstructorRegisterForm) => {
    try {
      clearError()
      // Prepare data for instructor registration
      const registrationData = {
        ...data,
        username: "", // Backend will auto-generate from email
      }

      // Use dedicated instructor registration endpoint
      await api.post("/auth/register-instructor", registrationData)

      toast.success("Registration successful! Your instructor account is pending admin approval. You will be notified once approved.")
      navigate("/login")
    } catch (err: any) {
      console.error("Full registration error:", err)
      console.error("Error response data:", err.response?.data)
      console.error("Error response status:", err.response?.status)

      if (err.response?.data?.detail) {
        const detail = err.response.data.detail
        console.error("Error detail:", detail)

        // Handle array of errors
        if (Array.isArray(detail)) {
          detail.forEach((error: any) => {
            const fieldName = error.loc ? error.loc.join('.') : 'Field'
            toast.error(`${fieldName}: ${error.msg}`)
          })
        } else if (typeof detail === 'string') {
          toast.error(detail)
        } else {
          toast.error(JSON.stringify(detail))
        }
      } else if (err.response?.data?.errors) {
        // Handle validation errors
        const errors = err.response.data.errors
        Object.keys(errors).forEach(key => {
          toast.error(`${key}: ${errors[key]}`)
        })
      } else {
        toast.error("Registration failed. Please check the console for details.")
      }
    }
  }

  const steps = [
    { number: 1, title: "Personal Info", icon: User },
    { number: 2, title: "Security", icon: Lock },
    { number: 3, title: "Professional Info", icon: Briefcase },
    { number: 4, title: "Review", icon: Check },
  ]

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle className="text-2xl">Become an Instructor</CardTitle>
        <CardDescription>
          Complete all steps to apply as an instructor
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Step Indicator */}
        <div className="flex items-center justify-between mb-8">
          {steps.map((step, index) => (
            <React.Fragment key={step.number}>
              <div className="flex flex-col items-center">
                <div
                  className={`w-12 h-12 rounded-full flex items-center justify-center border-2 transition-colors ${
                    currentStep >= step.number
                      ? "bg-blue-600 border-blue-600 text-white"
                      : "bg-white border-gray-300 text-gray-400"
                  }`}
                >
                  <step.icon className="w-5 h-5" />
                </div>
                <span className="text-xs mt-2 text-gray-600">{step.title}</span>
              </div>
              {index < steps.length - 1 && (
                <div
                  className={`flex-1 h-1 mx-2 transition-colors ${
                    currentStep > step.number ? "bg-blue-600" : "bg-gray-200"
                  }`}
                />
              )}
            </React.Fragment>
          ))}
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Step 1: Personal Info */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-700">First Name</label>
                  <Input
                    {...register("first_name")}
                    placeholder="John"
                    className="mt-1"
                  />
                  {errors.first_name && (
                    <p className="text-sm text-red-600 mt-1">{errors.first_name.message}</p>
                  )}
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">Last Name</label>
                  <Input
                    {...register("last_name")}
                    placeholder="Doe"
                    className="mt-1"
                  />
                  {errors.last_name && (
                    <p className="text-sm text-red-600 mt-1">{errors.last_name.message}</p>
                  )}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700">Email Address</label>
                <div className="relative mt-1">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <Input
                    {...register("email")}
                    type="email"
                    placeholder="john@example.com"
                    className={`pl-10 pr-10 ${emailExists ? 'border-red-500' : ''}`}
                  />
                  {emailCheckLoading && (
                    <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    </div>
                  )}
                  {!emailCheckLoading && watchedFields.email && !emailExists && (
                    <Check className="absolute right-3 top-1/2 transform -translate-y-1/2 text-green-600 w-5 h-5" />
                  )}
                </div>
                {errors.email && (
                  <p className="text-sm text-red-600 mt-1">{errors.email.message}</p>
                )}
                {emailExists && !errors.email && (
                  <p className="text-sm text-red-600 mt-1">This email is already registered</p>
                )}
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700">Phone Number</label>
                <div className="relative mt-1">
                  <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <Input
                    {...register("phone")}
                    type="tel"
                    placeholder="+1 234 567 8900"
                    className="pl-10"
                  />
                </div>
                {errors.phone && (
                  <p className="text-sm text-red-600 mt-1">{errors.phone.message}</p>
                )}
              </div>
            </div>
          )}

          {/* Step 2: Security */}
          {currentStep === 2 && (
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700">Password</label>
                <div className="relative mt-1">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <Input
                    {...register("password")}
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    className="pl-10 pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {errors.password && (
                  <p className="text-sm text-red-600 mt-1">{errors.password.message}</p>
                )}
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700">Confirm Password</label>
                <div className="relative mt-1">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <Input
                    {...register("confirm_password")}
                    type={showConfirmPassword ? "text" : "password"}
                    placeholder="••••••••"
                    className="pl-10 pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {errors.confirm_password && (
                  <p className="text-sm text-red-600 mt-1">{errors.confirm_password.message}</p>
                )}
              </div>
            </div>
          )}

          {/* Step 3: Professional Info */}
          {currentStep === 3 && (
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700">Designation / Title</label>
                <div className="relative mt-1">
                  <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <Input
                    {...register("designation")}
                    placeholder="e.g. Senior Web Developer, Data Scientist"
                    className="pl-10"
                  />
                </div>
                {errors.designation && (
                  <p className="text-sm text-red-600 mt-1">{errors.designation.message}</p>
                )}
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700">Professional Bio</label>
                <textarea
                  {...register("bio")}
                  placeholder="Tell us about yourself, your expertise, and teaching philosophy..."
                  className="w-full min-h-[120px] px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent mt-1"
                />
                <p className="text-xs text-gray-500 mt-1">Minimum 50 characters</p>
                {errors.bio && (
                  <p className="text-sm text-red-600 mt-1">{errors.bio.message}</p>
                )}
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700">Teaching Experience</label>
                <textarea
                  {...register("experience")}
                  placeholder="Describe your teaching experience, courses you've taught, and relevant achievements..."
                  className="w-full min-h-[120px] px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent mt-1"
                />
                {errors.experience && (
                  <p className="text-sm text-red-600 mt-1">{errors.experience.message}</p>
                )}
              </div>
            </div>
          )}

          {/* Step 4: Review */}
          {currentStep === 4 && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="font-semibold text-blue-900 mb-3">Review Your Information</h3>
                <div className="space-y-2 text-sm">
                  <p><span className="font-medium">Name:</span> {watchedFields.first_name} {watchedFields.last_name}</p>
                  <p><span className="font-medium">Email:</span> {watchedFields.email}</p>
                  <p><span className="font-medium">Phone:</span> {watchedFields.phone}</p>
                  <p><span className="font-medium">Designation:</span> {watchedFields.designation}</p>
                  <p><span className="font-medium">Bio:</span> {watchedFields.bio}</p>
                  <p><span className="font-medium">Experience:</span> {watchedFields.experience}</p>
                </div>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-sm text-yellow-900">
                  <strong>Note:</strong> Your instructor application will be reviewed by our admin team.
                  You will receive a notification once your account is approved.
                </p>
              </div>

              <div className="flex items-start space-x-2">
                <input
                  {...register("agree_to_terms")}
                  type="checkbox"
                  id="terms"
                  className="mt-1"
                />
                <label htmlFor="terms" className="text-sm text-gray-700">
                  I agree to the Terms of Service and Privacy Policy
                </label>
              </div>
              {errors.agree_to_terms && (
                <p className="text-sm text-red-600">{errors.agree_to_terms.message}</p>
              )}
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between pt-4">
            {currentStep > 1 && (
              <Button
                type="button"
                variant="outline"
                onClick={prevStep}
                className="flex items-center space-x-2"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Previous</span>
              </Button>
            )}

            {currentStep < 4 ? (
              <Button
                type="button"
                onClick={nextStep}
                className="ml-auto flex items-center space-x-2"
              >
                <span>Next</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            ) : (
              <Button
                type="submit"
                disabled={isLoading}
                className="ml-auto flex items-center space-x-2"
              >
                {isLoading ? "Submitting..." : "Submit Application"}
                <Check className="w-4 h-4" />
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
