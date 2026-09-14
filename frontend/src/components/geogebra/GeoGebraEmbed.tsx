/**
 * GeoGebra applet embed — loads the official deployggb.js Apps API and
 * injects the applet into a container div. Fires one xAPI "launched"
 * statement per mount through the SILEOS event spine (best-effort).
 *
 * LICENCE: GeoGebra Apps API — non-commercial use; commercial deployment
 * requires an agreement with GeoGebra GmbH (owner approved preview use).
 */
import { useEffect, useRef, useState } from 'react'
import { geogebraAPI } from '@/api/geogebra'
import { api } from '@/api/axios'

declare global {
  interface Window {
    // injected by deployggb.js
    GGBApplet?: new (params: Record<string, unknown>, autoLoad: boolean) => {
      inject: (el: HTMLElement | string) => void
    }
  }
}

const DEPLOY_URL = 'https://www.geogebra.org/apps/deployggb.js'

let scriptPromise: Promise<void> | null = null
function loadDeployGgb(): Promise<void> {
  if (typeof window === 'undefined') return Promise.reject(new Error('no window'))
  if (window.GGBApplet) return Promise.resolve()
  if (scriptPromise) return scriptPromise
  scriptPromise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${DEPLOY_URL}"]`)
    const script = existing ?? document.createElement('script')
    const timeout = window.setTimeout(() => {
      if (!window.GGBApplet) script.remove()
      reject(new Error('GeoGebra timed out while loading'))
    }, 15000)
    const loaded = () => {
      window.clearTimeout(timeout)
      if (window.GGBApplet) resolve()
      else reject(new Error('GeoGebra loaded without the Apps API'))
    }
    const failed = () => {
      window.clearTimeout(timeout)
      script.remove()
      reject(new Error('deployggb.js failed to load'))
    }
    script.addEventListener('load', loaded, { once: true })
    script.addEventListener('error', failed, { once: true })
    if (!existing) {
      script.src = DEPLOY_URL
      script.async = true
      document.head.appendChild(script)
    }
  }).catch((error) => {
    scriptPromise = null
    throw error
  })
  return scriptPromise
}

export function GeoGebraEmbed({
  appletId,
  lessonId,
  height = 480,
}: {
  appletId: number
  lessonId?: number
  height?: number
}) {
  const container = useRef<HTMLDivElement>(null)
  const injected = useRef(false)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    injected.current = false
    setError(null)
    if (container.current) container.current.replaceChildren()

    loadDeployGgb()
      .then(() => geogebraAPI.embed(appletId))
      .then((embed) => {
        if (cancelled) return
        const params = { ...embed.applet_parameters, height }
        const applet = new window.GGBApplet!(params, true)
        const el = container.current
        if (el) {
          applet.inject(el)
          injected.current = true
          // one statement per launch — best-effort, never blocks the player
          api.post('/xapi/statements', {
            verb: 'launched',
            object_type: 'geogebra',
            object_id: String(appletId),
            context: lessonId ? { lesson_id: lessonId, source: 'geogebra-embed' } : { source: 'geogebra-embed' },
          }).catch(() => undefined)
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load GeoGebra')
      })

    return () => { cancelled = true }
  }, [appletId, lessonId, height, attempt])

  if (error) {
    return (
      <div role="alert" className="p-4 border border-amber-200 bg-amber-50 rounded-lg text-sm text-amber-800">
        <p>GeoGebra could not load ({error}). Check your connection — the applet script is served from geogebra.org.</p>
        <button type="button" className="mt-3 rounded-md border border-amber-300 bg-white px-3 py-1.5 font-medium" onClick={() => setAttempt((value) => value + 1)}>
          Try again
        </button>
      </div>
    )
  }
  return (
    <div
      ref={container}
      className="w-full rounded-xl overflow-hidden border border-gray-200 bg-white"
      style={{ minHeight: height }}
      aria-label="GeoGebra interactive applet"
    />
  )
}

export default GeoGebraEmbed
