/**
 * Serialization between the designer's client-side DesignerElement (carries
 * a local `id` for React keys/selection/layers) and the plain
 * elements_config dict shape the backend stores/validates (no `id` field —
 * see backend/app/schemas/certificate.py DESIGNER_ELEMENT_TYPES + routers/
 * certificate_designer.py::validate_elements_config).
 */
import { makeElementId, type DesignerElement } from './certificateDesignerTypes'

/** Plain JSON-safe dict as the backend expects it (no client-only `id`). */
export type ServerElement = Omit<DesignerElement, 'id'> & Record<string, unknown>

/** Element -> server dict: drop the client-only id, drop undefined fields
 * (keeps payloads small and avoids sending `undefined` through JSON, which
 * silently becomes absence anyway but is clearer to do explicitly). */
export function toServerElement(el: DesignerElement): ServerElement {
  const { id, ...rest } = el
  const out: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(rest)) {
    if (value !== undefined) out[key] = value
  }
  return out as ServerElement
}

export function toServerElements(elements: DesignerElement[]): ServerElement[] {
  return elements.map(toServerElement)
}

/** Server dict -> element: assign a fresh client-only id (a server row
 * never carries one). Unknown/extra fields are preserved so a round-trip
 * never silently drops data the server sent back. */
export function fromServerElement(raw: Record<string, unknown>): DesignerElement {
  return {
    ...(raw as object),
    id: makeElementId(),
  } as DesignerElement
}

export function fromServerElements(raw: Record<string, unknown>[]): DesignerElement[] {
  return (raw || []).map(fromServerElement)
}

/**
 * True when two server-shaped element lists are semantically identical
 * (same length, each element's own keys deep-equal) — used for the
 * add/edit -> serialize -> deserialize -> re-serialize round-trip test, and
 * usable by callers wanting a "has this template actually changed" check
 * (e.g. before pushing an autosave draft).
 */
export function serverElementsEqual(a: ServerElement[], b: ServerElement[]): boolean {
  if (a.length !== b.length) return false
  return a.every((el, i) => JSON.stringify(el) === JSON.stringify(b[i]))
}
