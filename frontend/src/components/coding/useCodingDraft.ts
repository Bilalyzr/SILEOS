import { useCallback, useEffect, useRef, useState } from 'react'
import { codingAPI, type CodingLanguage } from '@/api/coding'

export type DraftStatus = 'idle' | 'saving' | 'saved' | 'device-only'

/** Key for the per-device copy of a draft. Pure so it can be tested. */
export function draftKey(slug: string, language: CodingLanguage) {
  return `sileos-coding-draft:${slug}:${language}`
}

function readLocal(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeLocal(key: string, value: string) {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // Private mode or a full quota: the server copy still applies.
  }
}

/**
 * Keeps a learner's source for one challenge and language between visits.
 *
 * The server copy is the source of truth. A per-device copy in localStorage
 * is written first, so typing survives a dropped connection, and the server
 * is updated one second after the last keystroke.
 */
export function useCodingDraft(slug: string, language: CodingLanguage, debounceMs = 1000) {
  const [status, setStatus] = useState<DraftStatus>('idle')
  const timer = useRef<number | undefined>()

  useEffect(() => () => window.clearTimeout(timer.current), [])

  /** Returns the saved source for this challenge and language, or null if there is none. */
  const restore = useCallback(async (lang: CodingLanguage = language): Promise<string | null> => {
    try {
      const remote = await codingAPI.draft(slug, lang)
      if (remote) return remote.source_code
    } catch {
      // Fall through to the device copy.
    }
    return readLocal(draftKey(slug, lang))
  }, [slug, language])

  const save = useCallback((source: string) => {
    const key = draftKey(slug, language)
    writeLocal(key, source)
    window.clearTimeout(timer.current)
    setStatus('saving')
    timer.current = window.setTimeout(async () => {
      try {
        await codingAPI.saveDraft(slug, language, source)
        setStatus('saved')
      } catch {
        setStatus('device-only')
      }
    }, debounceMs)
  }, [slug, language, debounceMs])

  return { restore, save, status }
}
