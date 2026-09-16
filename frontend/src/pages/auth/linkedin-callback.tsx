import { useEffect } from 'react'

export const LinkedInCallbackPage = () => {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const state = params.get('state')
    const storedState = localStorage.getItem('linkedin_state')

    if (!code) {
      window.location.href = '/login?error=linkedin_failed'
      return
    }

    if (state !== storedState) {
      window.location.href = '/login?error=invalid_state'
      return
    }

    // Exchange code for token
    fetch('/api/v1/auth/linkedin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    })
    .then(res => res.json())
    .then(data => {
      if (data.access_token) {
        const existing = JSON.parse(localStorage.getItem('auth-storage') || '{"state":{}}')
        existing.state.accessToken = data.access_token
        existing.state.refreshToken = null
        existing.state.isAuthenticated = true
        existing.state.user = data.user || null
        localStorage.setItem('auth-storage', JSON.stringify(existing))
        window.location.href = '/dashboard'
      } else {
        window.location.href = '/login?error=linkedin_failed'
      }
    })
    .catch(() => {
      window.location.href = '/login?error=linkedin_failed'
    })
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
        <p className="text-gray-600">Completing LinkedIn login...</p>
      </div>
    </div>
  )
}
