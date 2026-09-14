import { describe, expect, it } from 'vitest'
import { lessonContentSyncPayload } from '../lessonContentSync'

describe('lessonContentSyncPayload', () => {
  it('video -> h5p pick: contentType flip alone syncs nothing (avoids the type-only 400)', () => {
    expect(lessonContentSyncPayload('contentType', 'h5p')).toEqual({})
  })

  it('video -> h5p pick: choosing an h5pContentId syncs the atomic pair', () => {
    expect(lessonContentSyncPayload('h5pContentId', 42)).toEqual({
      lesson_content_type: 'h5p',
      h5p_content_id: 42,
    })
  })

  it('video -> game pick: contentType flip alone syncs nothing (avoids the type-only 400)', () => {
    expect(lessonContentSyncPayload('contentType', 'game')).toEqual({})
  })

  it('video -> game pick: choosing a gameId syncs the atomic pair', () => {
    expect(lessonContentSyncPayload('gameId', 7)).toEqual({
      lesson_content_type: 'game',
      game_id: 7,
    })
  })

  it('-> video flip: syncs the type alone (server clears both FKs)', () => {
    expect(lessonContentSyncPayload('contentType', 'video')).toEqual({
      lesson_content_type: 'video',
    })
  })

  it('h5p -> game switch: null-ing out h5pContentId syncs nothing', () => {
    expect(lessonContentSyncPayload('h5pContentId', null)).toEqual({})
  })

  it('h5p -> game switch: picking a gameId syncs the game pair', () => {
    expect(lessonContentSyncPayload('gameId', 3)).toEqual({
      lesson_content_type: 'game',
      game_id: 3,
    })
  })

  it('game -> h5p switch: null-ing out gameId syncs nothing', () => {
    expect(lessonContentSyncPayload('gameId', null)).toEqual({})
  })

  it('game -> h5p switch: picking an h5pContentId syncs the h5p pair', () => {
    expect(lessonContentSyncPayload('h5pContentId', 11)).toEqual({
      lesson_content_type: 'h5p',
      h5p_content_id: 11,
    })
  })

  it('unrecognized field returns an empty payload', () => {
    // @ts-expect-error - exercising the runtime default branch
    expect(lessonContentSyncPayload('unknown', 'x')).toEqual({})
  })
})
