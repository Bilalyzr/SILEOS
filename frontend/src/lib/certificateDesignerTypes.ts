/**
 * Shared types for the certificate designer (plan Task 7, spec section C
 * item 4). Mirrors the backend elements_config shape validated in
 * backend/app/routers/certificate_designer.py::validate_elements_config and
 * rendered in backend/app/services/certificate_html_renderer.py — every
 * field here has a server-side counterpart validator; the client mirrors
 * those rules so instructors get instant feedback, but the server remains
 * the authority (final validation always happens there too).
 */

/** The 11 designer element types the backend accepts (DESIGNER_ELEMENT_TYPES
 * in backend/app/schemas/certificate.py). "student_name" etc. are typed
 * tokens substituted server-side; "text"/"image"/"rect"/"line"/"qr_code"/
 * "signature_image" are free-form. */
export type ElementType =
  | 'text'
  | 'student_name'
  | 'course_name'
  | 'completion_date'
  | 'certificate_id'
  | 'instructor_name'
  | 'qr_code'
  | 'signature_image'
  | 'image'
  | 'rect'
  | 'line'

export const ELEMENT_TYPES: ElementType[] = [
  'text',
  'student_name',
  'course_name',
  'completion_date',
  'certificate_id',
  'instructor_name',
  'qr_code',
  'signature_image',
  'image',
  'rect',
  'line',
]

/** Typed tokens that resolve to real data server-side — no free-text
 * content field, nothing to type in the properties panel besides styling. */
export const TOKEN_ELEMENT_TYPES: ElementType[] = [
  'student_name',
  'course_name',
  'completion_date',
  'certificate_id',
  'instructor_name',
]

export type BorderStyle = 'solid' | 'dashed' | 'dotted'

export interface ElementBorder {
  width: number
  style: BorderStyle
  color: string
}

export interface DesignerElement {
  /** Client-only stable id for React keys / selection — NOT sent to the
   * server as-is (the backend doesn't require or store an id field on each
   * element; we keep one locally for diffing/undo/layers). */
  id: string
  type: ElementType
  x: number
  y: number
  width: number
  height: number
  rotation?: number
  z_index: number

  // text-ish fields (text, student_name, course_name, completion_date,
  // certificate_id, instructor_name)
  content?: string
  font_family?: string | null
  font_size?: number
  font_color?: string
  font_weight?: string
  text_align?: 'left' | 'center' | 'right'
  letter_spacing?: number | null
  background_color?: string

  // image / signature_image
  image_url?: string
  src?: string

  // rect
  fill?: string
  border_radius?: number

  // line
  line_color?: string
  line_thickness?: number

  // shared
  border?: ElementBorder | string | null
}

export type Orientation = 'landscape' | 'portrait'

export interface DesignerTemplate {
  id: number
  name: string
  description: string
  orientation: Orientation
  certificate_width: number
  certificate_height: number
  background_color: string
  background_image: string
  elements_config: DesignerElement[]
  is_global: boolean
  is_own: boolean
  post_author: number
  created_at?: string | null
  updated_at?: string | null
  /** Real Chrome-rendered preview PNG URL when one exists on disk (Task 8
   * fix round D-8) — null/undefined falls back to the gallery's CSS-swatch
   * placeholder. */
  thumbnail?: string | null
}

/** Orientation/size presets (plan Task 7 binding). */
export const SIZE_PRESETS: Record<string, { label: string; width: number; height: number; orientation: Orientation }> = {
  a4_landscape: { label: 'A4 Landscape', width: 1123, height: 794, orientation: 'landscape' },
  a4_portrait: { label: 'A4 Portrait', width: 794, height: 1123, orientation: 'portrait' },
  square: { label: 'Square', width: 1000, height: 1000, orientation: 'landscape' },
}

export const ZOOM_MIN = 50
export const ZOOM_MAX = 150
export const ZOOM_DEFAULT = 100

export const MAX_ELEMENTS = 100

let idCounter = 0
/** Deterministic-enough unique id for a new element (client-only, never
 * sent to the server as a field the backend validates). */
export function makeElementId(): string {
  idCounter += 1
  return `el-${Date.now().toString(36)}-${idCounter}-${Math.random().toString(36).slice(2, 8)}`
}
