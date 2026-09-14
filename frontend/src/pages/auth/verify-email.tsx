import { AstraSymbol } from "@/components/design-system/AstraSymbol";
import { useEffect,useState } from 'react'
import { useNavigate,useSearchParams,Link } from 'react-router-dom'
import { Card,CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CheckCircle,XCircle,Loader2,Info } from 'lucide-react'
import { api } from '@/api/axios'

export const VerifyEmailPage = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'already-verified'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    const verifyEmail = async () => {
      const token = searchParams.get('token')

      if (!token) {
        setStatus('error')
        setMessage('Invalid verification link. No token provided.')
        return
      }

      try {
        const response = await api.post(`/auth/verify-email`, {
          token
        })

        setStatus('success')
        setMessage(response.data.message || 'Email verified successfully!')

        // Redirect to login after 3 seconds
        setTimeout(() => {
          navigate('/login?verified=true')
        }, 3000)

      } catch (error: any) {
        console.error('Verification error:', error)

        const errorDetail = error.response?.data?.detail || ''

        // Check if email is already verified
        if (errorDetail.toLowerCase().includes('already verified') ||
            errorDetail.toLowerCase().includes('already been verified')) {
          setStatus('already-verified')
          setMessage('Your email has already been verified. You can proceed to login.')

          // Redirect to login after 3 seconds
          setTimeout(() => {
            navigate('/login?verified=true')
          }, 3000)
        } else {
          setStatus('error')

          if (errorDetail) {
            setMessage(errorDetail)
          } else if (error.response?.status === 400) {
            setMessage('Invalid or expired verification link.')
          } else {
            setMessage('Verification failed. Please try again or contact support.')
          }
        }
      }
    }

    verifyEmail()
  }, [searchParams, navigate])

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="text-center space-y-4">
              <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
                <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900">Verifying your email...</h2>
              <p className="text-gray-600">
                Please wait while we verify your email address.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (status === 'success' || status === 'already-verified') {
    const isAlreadyVerified = status === 'already-verified'

    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="text-center space-y-4">
              <div className={`mx-auto w-16 h-16 rounded-full flex items-center justify-center ${
                isAlreadyVerified ? 'bg-blue-100' : 'bg-green-100'
              }`}>
                {isAlreadyVerified ? (
                  <Info className="w-10 h-10 text-blue-600" />
                ) : (
                  <CheckCircle className="w-10 h-10 text-green-600" />
                )}
              </div>
              <h2 className="text-2xl font-bold text-gray-900">
                {isAlreadyVerified ? 'Already Verified!' : 'Email Verified!'}
              </h2>
              <p className="text-gray-600">{message}</p>
              <div className={`border rounded-lg p-4 ${
                isAlreadyVerified
                  ? 'bg-blue-50 border-blue-200'
                  : 'bg-green-50 border-green-200'
              }`}>
                <p className={`text-sm ${isAlreadyVerified ? 'text-blue-900' : 'text-green-900'}`}>
                  {isAlreadyVerified ? (
                    <>
                      <AstraSymbol value="ℹ️" /> <strong>Your email is already verified</strong>
                    </>
                  ) : (
                    <>
                      <AstraSymbol value="🎉" /> <strong>Your account is now active!</strong>
                    </>
                  )}
                </p>
                <p className={`text-xs mt-2 ${isAlreadyVerified ? 'text-blue-800' : 'text-green-800'}`}>
                  You can now sign in and start learning.
                </p>
              </div>
              <p className="text-sm text-gray-600">
                Redirecting to login page...
              </p>
              <Button
                onClick={() => navigate('/login')}
                className="w-full"
              >
                Proceed to Login
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Error state
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <Card className="w-full max-w-md">
        <CardContent className="pt-6">
          <div className="text-center space-y-4">
            <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
              <XCircle className="w-10 h-10 text-red-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Verification Failed</h2>
            <p className="text-gray-600">{message}</p>
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-sm text-red-900">
                <strong>Common reasons:</strong>
              </p>
              <ul className="text-xs text-red-800 mt-2 text-left list-disc list-inside">
                <li>Verification link has expired (24 hours)</li>
                <li>Email already verified</li>
                <li>Invalid verification token</li>
              </ul>
            </div>
            <div className="space-y-2">
              <Button
                onClick={() => navigate('/register')}
                className="w-full"
              >
                Register Again
              </Button>
              <Button
                onClick={() => navigate('/login')}
                variant="outline"
                className="w-full"
              >
                Go to Login
              </Button>
            </div>
            <p className="text-xs text-gray-500">
              Need help? <Link to="/contact" className="text-blue-600 hover:underline">Contact Support</Link>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
