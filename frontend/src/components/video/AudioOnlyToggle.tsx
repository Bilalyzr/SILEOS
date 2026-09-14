/**
 * AudioOnlyToggle (roadmap item 9): if an audio-only rendition (.m4a built
 * by ffmpeg next to the uploaded video) exists, offer it. Auto-selects when
 * the learner's data saver is on. YouTube sources have no rendition.
 */
import { useEffect, useState } from 'react'
import { readDataSaver } from '@/components/three-d/DeferredThreeD'

export function audioCandidate(src: string): string | null {
  if (!src || !/^\/uploads\/videos\//.test(src)) return null
  return src.replace(/\.[a-z0-9]+$/i, '.m4a')
}

export function AudioOnlyToggle({ src, value, onChange }: { src: string; value: string | null; onChange: (audioSrc: string | null) => void }) {
  const [available, setAvailable] = useState(false)
  const candidate = audioCandidate(src)
  useEffect(() => {
    let alive = true
    setAvailable(false)
    if (!candidate) return
    fetch(candidate, { method: 'HEAD' }).then((r) => {
      if (!alive) return
      const ok = r.ok && /audio|mp4|octet/.test(r.headers.get('content-type') || 'audio')
      setAvailable(ok)
      if (ok && readDataSaver()) onChange(candidate)
    }).catch(() => {})
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidate])
  if (!candidate || !available) return null
  const on = value === candidate
  return (
    <div className="absolute top-3 left-3 z-10">
      <button type="button" onClick={() => onChange(on ? null : candidate)} aria-pressed={on} data-testid="audio-only-toggle"
        className={`px-2.5 py-1 text-[11px] rounded-full border backdrop-blur ${on ? 'bg-amber-400 text-black border-amber-500' : 'bg-black/50 text-white border-white/30'}`}>
        {on ? 'Audio only: on (saves data)' : 'Audio only'}
      </button>
    </div>
  )
}

export default AudioOnlyToggle
