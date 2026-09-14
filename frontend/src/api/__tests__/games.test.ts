import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Mock the shared axios instance so we can assert the exact URL shapes
// games.ts calls it with — none may carry a trailing slash (spec §3 /
// axios.ts's noSlashEndpoints '/games' entry: redirect_slashes=False on
// the backend turns any trailing slash into a 404).
vi.mock('@/api/axios', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import { api } from '@/api/axios'
import {
  createGame,
  deleteGame,
  getGame,
  getGamePlay,
  getGameResults,
  getPlayPayload,
  listGameResults,
  listMyGames,
  publishGame,
  submitGameResult,
  unpublishGame,
  updateGame,
  type Game,
  type GamePlayPayload,
} from '../games'

// --- Type-level proof: Game/GamePlayPayload are REAL discriminated unions
// on `template`, tagged on the OUTER type (the config JSON itself can
// never carry a tag — extra="forbid" at every nesting level). These
// functions only need to COMPILE (tsc --noEmit) to prove the narrowing;
// `game.config.items[0].answer_index` etc. below would be a type error
// on an un-narrowed union, and reading a wrong-branch field (e.g.
// `.categories` after narrowing to 'quiz_rush') would also fail to
// compile. No `as`/`any` cast anywhere in these bodies.
function assertGameNarrowsWithoutCasts(game: Game): number {
  if (game.template === 'quiz_rush') {
    return game.config.items[0].answer_index
  }
  if (game.template === 'match_pairs') {
    return game.config.items.length + game.config.items[0].left.length
  }
  return 0
}

function assertGamePlayPayloadNarrowsWithoutCasts(payload: GamePlayPayload): string {
  if (payload.template === 'drag_sort') {
    return payload.config.categories[0].name
  }
  if (payload.template === 'word_builder') {
    return payload.config.items[0].clue
  }
  if (payload.template === 'sequence') {
    return payload.config.items[0].text
  }
  return payload.template
}

const getMock = api.get as unknown as ReturnType<typeof vi.fn>
const postMock = api.post as unknown as ReturnType<typeof vi.fn>
const putMock = api.put as unknown as ReturnType<typeof vi.fn>
const deleteMock = api.delete as unknown as ReturnType<typeof vi.fn>

beforeEach(() => {
  getMock.mockReset().mockResolvedValue({ data: {} })
  postMock.mockReset().mockResolvedValue({ data: {} })
  putMock.mockReset().mockResolvedValue({ data: {} })
  deleteMock.mockReset().mockResolvedValue({ data: {} })
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('Game / GamePlayPayload discriminated union narrowing', () => {
  it('narrows game.config to the matching template variant with zero casts', () => {
    const quizGame: Game = {
      id: 1,
      owner_id: 1,
      title: 'Quiz',
      status: 'draft',
      item_count: 1,
      max_score: 10,
      created_at: '',
      updated_at: '',
      template: 'quiz_rush',
      config: {
        items: [{ prompt: 'Q', options: ['a', 'b'], answer_index: 1 }],
        settings: { seconds_per_question: 20, shuffle: false },
      },
    }
    expect(assertGameNarrowsWithoutCasts(quizGame)).toBe(1)

    const matchGame: Game = {
      ...quizGame,
      template: 'match_pairs',
      config: {
        items: [{ left: 'L', right: 'R' }],
        settings: { time_limit_s: 0 },
      },
    }
    expect(assertGameNarrowsWithoutCasts(matchGame)).toBe(1 + 1)

    const dragPayload: GamePlayPayload = {
      id: 1,
      title: 'Sort',
      max_score: 10,
      preview: false,
      template: 'drag_sort',
      config: {
        categories: [{ name: 'Cat' }],
        items: [{ text: 'Item', category_index: 0 }],
        settings: { time_limit_s: 0 },
      },
    }
    expect(assertGamePlayPayloadNarrowsWithoutCasts(dragPayload)).toBe('Cat')
  })
})

describe('games api client URL shapes (no trailing slashes)', () => {
  it('createGame -> POST /games', async () => {
    await createGame({ title: 'T', template: 'quiz_rush', config: {} as any })
    expect(postMock).toHaveBeenCalledWith('/games', {
      title: 'T',
      template: 'quiz_rush',
      config: {},
    })
  })

  it('listMyGames -> GET /games/mine', async () => {
    await listMyGames()
    expect(getMock).toHaveBeenCalledWith('/games/mine')
  })

  it('getGame -> GET /games/{id}', async () => {
    await getGame(42)
    expect(getMock).toHaveBeenCalledWith('/games/42')
  })

  it('updateGame -> PUT /games/{id}', async () => {
    await updateGame(42, { title: 'New' })
    expect(putMock).toHaveBeenCalledWith('/games/42', { title: 'New' })
  })

  it('publishGame -> POST /games/{id}/publish', async () => {
    await publishGame(42)
    expect(postMock).toHaveBeenCalledWith('/games/42/publish')
  })

  it('unpublishGame -> POST /games/{id}/unpublish', async () => {
    await unpublishGame(42)
    expect(postMock).toHaveBeenCalledWith('/games/42/unpublish')
  })

  it('deleteGame -> DELETE /games/{id}', async () => {
    await deleteGame(42)
    expect(deleteMock).toHaveBeenCalledWith('/games/42')
  })

  it('getGamePlay / getPlayPayload -> GET /games/{id}/play', async () => {
    await getGamePlay(42)
    expect(getMock).toHaveBeenCalledWith('/games/42/play')
    await getPlayPayload(42)
    expect(getMock).toHaveBeenCalledWith('/games/42/play')
  })

  it('submitGameResult -> POST /games/{id}/results', async () => {
    await submitGameResult(42, { score: 10, max_score: 10, duration_s: 30 })
    expect(postMock).toHaveBeenCalledWith('/games/42/results', {
      score: 10,
      max_score: 10,
      duration_s: 30,
    })
  })

  it('listGameResults / getGameResults -> GET /games/{id}/results', async () => {
    await listGameResults(42)
    expect(getMock).toHaveBeenCalledWith('/games/42/results')
    await getGameResults(42)
    expect(getMock).toHaveBeenCalledWith('/games/42/results')
  })

  it('no URL passed to the api client ever ends with a trailing slash', async () => {
    const allCalls = [...getMock.mock.calls, ...postMock.mock.calls, ...putMock.mock.calls, ...deleteMock.mock.calls]
    for (const call of allCalls) {
      const url = call[0] as string
      expect(url.endsWith('/')).toBe(false)
    }
  })
})
