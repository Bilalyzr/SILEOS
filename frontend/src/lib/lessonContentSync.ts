/**
 * Shared field→payload mapping for the video-lecture content sub-select
 * (Video | H5P interactive | Learning game) used by BOTH course editors
 * (edit-course.tsx and create-course.tsx).
 *
 * The backend validates (lesson_content_type, h5p_content_id, game_id) as
 * an atomic set: `lesson_content_type='h5p'` requires `h5p_content_id` in
 * the SAME PATCH, `lesson_content_type='game'` requires `game_id` in the
 * SAME PATCH — a type-only PATCH to either is a 400. This mirrors the
 * pattern commit 6d937c3 established for h5p alone:
 *   - flipping the sub-select to 'video' syncs ONLY the type — the server
 *     clears both FKs.
 *   - flipping the sub-select to 'h5p' or 'game' syncs NOTHING by itself
 *     (there is no id yet); the pair ships together once content is
 *     actually picked, via the 'h5pContentId'/'gameId' field.
 *   - picking an h5pContentId syncs {lesson_content_type:'h5p',
 *     h5p_content_id} together.
 *   - picking a gameId syncs {lesson_content_type:'game', game_id}
 *     together.
 *
 * Extracted out of the two page components so the mapping can't drift
 * between them, and so it's unit-testable without React/DOM.
 */

export type LessonContentSyncField = 'contentType' | 'h5pContentId' | 'gameId' | 'geogebraAppletId' | 'threeDModelId' | 'virtualLabSim'

export type LessonContentSyncValue = 'video' | 'h5p' | 'game' | 'geogebra' | 'three_d' | 'virtual_lab' | number | string | null

export interface LessonContentSyncPayload {
  lesson_content_type?: 'video' | 'h5p' | 'game' | 'geogebra' | 'three_d' | 'virtual_lab'
  h5p_content_id?: number
  game_id?: number
  geogebra_applet_id?: number
  three_d_model_id?: number
  virtual_lab_sim?: string
}

/**
 * Returns the PATCH fields to sync for one of the three content-sync
 * fields, or an empty object when nothing should sync yet (e.g.
 * contentType flipped to 'h5p'/'game' before an id has been picked —
 * syncing type alone there would be the exact 400 this helper exists to
 * prevent).
 */
export function lessonContentSyncPayload(
  field: LessonContentSyncField,
  value: LessonContentSyncValue
): LessonContentSyncPayload {
  if (field === 'contentType') {
    // Only the flip back to video syncs alone — the server clears both FKs.
    if (value === 'video') return { lesson_content_type: 'video' }
    return {}
  }

  if (field === 'h5pContentId') {
    if (value != null) {
      return { lesson_content_type: 'h5p', h5p_content_id: value as number }
    }
    return {}
  }

  if (field === 'threeDModelId') {
    if (value != null) {
      return { lesson_content_type: 'three_d', three_d_model_id: value as number }
    }
    return {}
  }

  if (field === 'virtualLabSim') {
    if (value != null && value !== '') {
      return { lesson_content_type: 'virtual_lab', virtual_lab_sim: value as string }
    }
    return {}
  }

  if (field === 'geogebraAppletId') {
    if (value != null) {
      return { lesson_content_type: 'geogebra', geogebra_applet_id: value as number }
    }
    return {}
  }

  if (field === 'gameId') {
    if (value != null) {
      return { lesson_content_type: 'game', game_id: value as number }
    }
    return {}
  }

  return {}
}
