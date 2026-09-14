/**
 * localStorage draft autosave for the certificate designer (plan Task 7
 * binding: "localStorage draft autosave (keyed per template id, restore
 * prompt on open, cleared on save) — wrap in try/catch"). "new" templates
 * (not yet saved) use the key segment "new" so a draft survives a refresh
 * before the first Save.
 */
import type { DesignerElement, Orientation } from './certificateDesignerTypes'

export interface DesignerDraft {
  templateKey: string
  elements: DesignerElement[]
  background_color: string
  background_image: string
  orientation: Orientation
  certificate_width: number
  certificate_height: number
  savedAt: string
}

const KEY_PREFIX = 'cert-designer-draft:'

export function draftKey(templateId: number | 'new'): string {
  return `${KEY_PREFIX}${templateId}`
}

export function saveDraft(templateId: number | 'new', draft: Omit<DesignerDraft, 'templateKey' | 'savedAt'>): void {
  try {
    const payload: DesignerDraft = {
      ...draft,
      templateKey: String(templateId),
      savedAt: new Date().toISOString(),
    }
    window.localStorage.setItem(draftKey(templateId), JSON.stringify(payload))
  } catch {
    // localStorage unavailable (private mode, quota, disabled) — autosave
    // is a convenience, never allowed to break the editor.
  }
}

export function loadDraft(templateId: number | 'new'): DesignerDraft | null {
  try {
    const raw = window.localStorage.getItem(draftKey(templateId))
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed || !Array.isArray(parsed.elements)) return null
    return parsed as DesignerDraft
  } catch {
    return null
  }
}

export function clearDraft(templateId: number | 'new'): void {
  try {
    window.localStorage.removeItem(draftKey(templateId))
  } catch {
    // best-effort — nothing to recover from here either.
  }
}
