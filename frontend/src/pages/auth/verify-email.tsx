import { useEffect,useState, type ReactNode } from 'react'
import { useNavigate,useSearchParams,Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { CheckCircle,Info,MailX } from 'lucide-react'
import { api } from '@/api/axios'
import { MagneticButton } from '@/components/auth/gateway/GatewayControls'
import { InfinityTrace } from '@/components/loading/InfinityTrace'

/** Status badge for the gateway panel: teal for done, amber for attention. */
function StatusMark({ tone, children }: { tone: 'teal' | 'amber'; children: ReactNode }) {
  const teal = tone === 'teal'
  return (
    <motion.div
      className={`mx-auto grid h-16 w-16 place-items-center rounded-2xl ${
        teal
          ? 'bg-[rgba(45,212,191,0.12)] text-[#2dd4bf] shadow-[0_0_0_1px_rgba(45,212,191,0.3)_inset,0_0_40px_rgba(45,212,191,0.25)]'
          : 'bg-[rgba(253,186,116,0.1)] text-[#fdba74] shadow-[0_0_0_1px_rgba(253,186,116,0.3)_inset]'
      }`}
      initial={{ rotate: -12, scale: 0.6 }}
      animate={{ rotate: 0, scale: 1 }}
      transition={{ type: 'spring', stiffness: 300, damping: 16 }}
      aria-hidden="true"
    >
      {children}
    </motion.div>
  )
}

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
      <div className="w-full py-2 text-center" role="status">
        <InfinityTrace label="Verifying your email" />
      </div>
    )
  }

  if (status === 'success' || status === 'already-verified') {
    const isAlreadyVerified = status === 'already-verified'

    return (
      <div className="w-full py-1 text-center" role="status">
        <StatusMark tone="teal">
          {isAlreadyVerified ? <Info className="h-8 w-8" /> : <CheckCircle className="h-8 w-8" />}
        </StatusMark>
        <div className="ag-head mt-5">
          <h2>{isAlreadyVerified ? 'Already verified' : 'Email verified'}</h2>
          <p>{message}</p>
        </div>
        <div className="ag-callout is-teal text-left">
          <h3>{isAlreadyVerified ? 'Your email was already confirmed' : 'Your account is active'}</h3>
          <p>You can sign in and start learning.</p>
        </div>
        <p className="ag-foot">Taking you to sign in…</p>
        <div className="mt-3">
          <MagneticButton type="button" onClick={() => navigate('/login')}>
            Continue to sign in
          </MagneticButton>
        </div>
      </div>
    )
  }

  // Error state
  return (
    <div className="w-full py-1 text-center">
      <StatusMark tone="amber">
        <MailX className="h-8 w-8" />
      </StatusMark>
      <div className="ag-head mt-5">
        <h2>This link didn't work</h2>
        <p>{message}</p>
      </div>
      <div className="ag-callout text-left">
        <h3>Usually it's one of these</h3>
        <ul className="mt-1 list-inside list-disc space-y-0.5 text-[13.5px] text-[#a9b4c6]">
          <li>The link is older than 24 hours</li>
          <li>Your email is already verified (try signing in)</li>
          <li>The link was copied only partly</li>
        </ul>
      </div>
      <div className="mt-4 grid gap-3">
        <MagneticButton type="button" onClick={() => navigate('/login')}>
          Go to sign in
        </MagneticButton>
        <button type="button" className="ag-ghost w-full" onClick={() => navigate('/register')}>
          Create an account again
        </button>
      </div>
      <p className="ag-foot">
        Need help? <Link to="/contact" className="ag-link">Contact support</Link>
      </p>
    </div>
  )
}
