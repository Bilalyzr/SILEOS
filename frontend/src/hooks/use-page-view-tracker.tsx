import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { api } from '@/api/axios'

const SESSION_KEY = 'sashalms_session_id'

function getSessionId(): string {
  try {
    let sid = sessionStorage.getItem(SESSION_KEY)
    if (!sid) {
      sid = (crypto?.randomUUID?.() || Math.random().toString(36).slice(2) + Date.now().toString(36))
      sessionStorage.setItem(SESSION_KEY, sid)
    }
    return sid
  } catch {
    return ''
  }
}

function detectEntity(path: string): { entity_type?: string; entity_id?: number } {
  const courseMatch = path.match(/^\/course\/(\d+)/) || path.match(/^\/courses\/(\d+)/)
  if (courseMatch) return { entity_type: 'course', entity_id: Number(courseMatch[1]) }

  const blogMatch = path.match(/^\/blog\/([^/]+)/)
  if (blogMatch && /^\d+$/.test(blogMatch[1])) {
    return { entity_type: 'blog', entity_id: Number(blogMatch[1]) }
  }
  const internshipMatch = path.match(/^\/internships?\/(\d+)/)
  if (internshipMatch) return { entity_type: 'internship', entity_id: Number(internshipMatch[1]) }

  return {}
}

/**
 * Fires a lightweight beacon to /api/v1/analytics/track on every client-side
 * route change. Mount once near the top of the tree (e.g. in App.tsx).
 * Also sends a best-effort duration_ms when the user leaves the page.
 */
export function usePageViewTracker() {
  const location = useLocation()
  const enteredAtRef = useRef<number>(Date.now())
  const lastPathRef = useRef<string>('')

  useEffect(() => {
    const path = location.pathname + (location.search || '')
    if (path === lastPathRef.current) return

    // Fire the previous path's duration before we switch
    if (lastPathRef.current) {
      const duration = Date.now() - enteredAtRef.current
      const prev = lastPathRef.current
      const entity = detectEntity(prev)
      api
        .post('/analytics/track', {
          path: prev,
          referrer: document.referrer || '',
          session_id: getSessionId(),
          duration_ms: duration,
          ...entity,
        })
        .catch(() => {})
    }

    // Record the new view with duration_ms=0; duration is filled on next change.
    lastPathRef.current = path
    enteredAtRef.current = Date.now()
    const entity = detectEntity(path)
    api
      .post('/analytics/track', {
        path,
        referrer: document.referrer || '',
        session_id: getSessionId(),
        duration_ms: 0,
        ...entity,
      })
      .catch(() => {})
  }, [location.pathname, location.search])

  // Best-effort flush on unload.
  useEffect(() => {
    const onHide = () => {
      if (!lastPathRef.current) return
      const duration = Date.now() - enteredAtRef.current
      const entity = detectEntity(lastPathRef.current)
      const payload = JSON.stringify({
        path: lastPathRef.current,
        referrer: document.referrer || '',
        session_id: getSessionId(),
        duration_ms: duration,
        ...entity,
      })
      try {
        navigator.sendBeacon?.('/api/v1/analytics/track', new Blob([payload], { type: 'application/json' }))
      } catch {
        /* noop */
      }
    }
    window.addEventListener('pagehide', onHide)
    return () => window.removeEventListener('pagehide', onHide)
  }, [])
}
