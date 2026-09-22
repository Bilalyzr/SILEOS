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
  scriptPromise ??= new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${DEPLOY_URL}"]`)
    const script = existing ?? document.createElement('script')
    script.addEventListener('load', () => resolve())
    script.addEventListener('error', () => reject(new Error('deployggb.js failed to load')))
    if (!existing) {
      script.src = DEPLOY_URL
      script.async = true
      document.head.appendChild(script)
    }
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
  const containerId = `geogebra-container-${appletId}`
  const injected = useRef(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    injected.current = false

    loadDeployGgb()
      .then(() => geogebraAPI.embed(appletId))
      .then((embed) => {
        if (cancelled) return
        const params = { ...embed.applet_parameters, height }
        const applet = new window.GGBApplet!(params, true)
        const el = document.getElementById(containerId)
        if (el) {
          applet.inject(containerId)
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
  }, [appletId, containerId, lessonId, height])

  if (error) {
    return (
      <div role="alert" className="p-4 border border-amber-200 bg-amber-50 rounded-lg text-sm text-amber-800">
        GeoGebra could not load ({error}). Check your connection — the applet
        script is served from geogebra.org.
      </div>
    )
  }
  return (
    <div
      id={containerId}
      className="w-full rounded-xl overflow-hidden border border-gray-200 bg-white"
      style={{ minHeight: height }}
      aria-label="GeoGebra interactive applet"
    />
  )
}

export default GeoGebraEmbed
