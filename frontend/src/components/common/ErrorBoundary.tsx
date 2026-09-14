import React from 'react'

interface ErrorBoundaryProps {
  children: React.ReactNode
  /**
   * Changing this value clears the caught error. Pass the current route (see
   * RouteErrorBoundary in App.tsx) so navigating away from a page that threw
   * recovers on its own, instead of stranding the user on the fallback until
   * they reload.
   */
  resetKey?: string
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

/**
 * Checks whether the error is a network / connection issue that warrants
 * showing the "server down" page instead of a generic error card.
 */
function isNetworkError(error: Error): boolean {
  const msg = error?.message?.toLowerCase() ?? ''
  // Common network / connection failure patterns
  return (
    msg.includes('network error') ||
    msg.includes('network request failed') ||
    msg.includes('failed to fetch') ||
    msg.includes('net::err_') ||
    msg.includes('err_network') ||
    msg.includes('err_connection') ||
    msg.includes('err_internet_disconnected') ||
    msg.includes('err_name_not_resolved') ||
    msg.includes('err_connection_refused') ||
    msg.includes('err_connection_reset') ||
    msg.includes('err_timed_out') ||
    msg.includes('socket hang up') ||
    msg.includes('econnrefused') ||
    msg.includes('econnreset') ||
    msg.includes('unable to connect') ||
    msg.includes('server is down') ||
    msg.includes('service unavailable') ||
    msg.includes('502') ||
    msg.includes('503')
  )
}

/**
 * App-wide error boundary. Without this, any render-time exception in a page
 * (e.g. a null field a component didn't guard) unmounts the whole React tree
 * and leaves the user on a blank white screen. Here we catch it and show a
 * recoverable fallback instead — the rest of the site (and a reload) still work.
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Log for production monitoring; a real Sentry/LogRocket hook can go here.
    console.error('Unhandled render error:', error, info?.componentStack)
  }

  componentDidUpdate(prev: ErrorBoundaryProps) {
    if (this.state.hasError && prev.resetKey !== this.props.resetKey) {
      this.setState({ hasError: false, error: null })
    }
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null })
    window.location.reload()
  }

  handleGoToServerDown = () => {
    this.setState({ hasError: false, error: null })
    window.location.href = '/server-down'
  }

  render() {
    if (this.state.hasError) {
      const isNetwork = this.state.error != null && isNetworkError(this.state.error)

      if (isNetwork) {
        return (
          <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-blue-50 px-4">
            <div className="max-w-md w-full text-center">
              {/* Animated pulse ring */}
              <div className="relative mx-auto mb-6 h-20 w-20">
                <div className="absolute inset-0 rounded-full bg-red-400/20 animate-ping" />
                <div className="absolute inset-2 rounded-full bg-red-100 flex items-center justify-center">
                  <svg
                    className="h-8 w-8 text-red-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M18.364 5.636a9 9 0 010 12.728M5.636 18.364a9 9 0 010-12.728M12 12h.008M12 16h.008M12 8h.008"
                    />
                  </svg>
                </div>
              </div>

              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                Connection Error
              </h1>
              <p className="text-sm text-gray-600 mb-6">
                We can't reach the server right now. It might be down for
                maintenance or experiencing issues. Check the status page for
                more details.
              </p>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                <button
                  onClick={this.handleGoToServerDown}
                  className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-gradient-to-r from-orange-400 via-orange-500 to-orange-600 text-white text-sm font-semibold shadow-[0_10px_24px_rgba(244,145,26,0.35)] transition hover:-translate-y-0.5"
                >
                  View Status Page
                </button>
                <button
                  onClick={this.handleReload}
                  className="w-full sm:w-auto px-5 py-2.5 rounded-xl ring-1 ring-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-semibold transition"
                >
                  Try Again
                </button>
              </div>
            </div>
          </div>
        )
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
          <div className="max-w-md w-full text-center bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
            <div className="mx-auto mb-4 w-14 h-14 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center text-2xl">
              !
            </div>
            <h1 className="text-xl font-bold text-gray-900 mb-2">Something went wrong</h1>
            <p className="text-sm text-gray-600 mb-6">
              This page hit an unexpected error. Reloading usually fixes it.
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={this.handleReload}
                className="px-5 py-2.5 rounded-xl bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold transition"
              >
                Reload page
              </button>
              <a
                href="/"
                className="px-5 py-2.5 rounded-xl ring-1 ring-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-semibold transition"
              >
                Go home
              </a>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
