/**
 * GamePicker — curriculum picker (spec §6): the instructor's own PUBLISHED
 * games + a "Create new game" link into the library. value/onChange carry
 * the Game integer id (the lessons.game_id FK) — mirrors H5PPicker's
 * value semantics.
 */
import * as React from 'react'
import { listMarketplaceGames } from '@/api/games'
import { Link } from 'react-router-dom'
import { Loader2,AlertTriangle,RefreshCw,Gamepad2,CheckCircle2,Eye,X } from 'lucide-react'
import { listMyGames,type GameSummary } from '@/api/games'
import { GamePlayer } from './GamePlayer'

export interface GamePickerProps {
  value?: number | null
  onChange: (gameId: number | null) => void
  className?: string
}

export const GamePicker: React.FC<GamePickerProps> = ({ value, onChange, className = '' }) => {
  const [games, setGames] = React.useState<GameSummary[]>([])
  const [marketplace, setMarketplace] = React.useState<{ id: number; title: string; owner_id: number }[]>([])
  const [loading, setLoading] = React.useState(true)
  const [loadError, setLoadError] = React.useState<string | null>(null)
  const [previewOpen, setPreviewOpen] = React.useState(false)

  const refresh = React.useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const res = await listMyGames()
      setGames(res.games.filter((g) => g.status === 'published'))
      try {
        const own = new Set(res.games.map((g) => g.id))
        const mkt = await listMarketplaceGames()
        setMarketplace(mkt.filter((m) => !own.has(m.id)))
      } catch { /* marketplace section is optional */ }
    } catch (err: any) {
      setLoadError(err?.response?.data?.detail || 'Failed to load your games')
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    refresh()
  }, [refresh])


  const selectedGame = games.find((g) => g.id === value)

  return (
    <div className={`space-y-2 ${className}`}>
      {marketplace.length > 0 && (
        <div className="border border-violet-200 bg-violet-50 rounded-lg p-3">
          <p className="text-xs font-semibold text-violet-800 mb-2">🛒 Prebuilt & marketplace games (admin packs and other instructors)</p>
          <div className="space-y-1">
            {marketplace.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => onChange?.(m.id)}
                className={`w-full text-left text-sm px-3 py-2 rounded-lg border ${
                  value === m.id ? 'border-violet-500 bg-white' : 'border-gray-200 bg-white hover:border-violet-400'
                }`}
              >
                🎮 {m.title} <span className="text-xs text-gray-400">by instructor #{m.owner_id}</span>
                {value === m.id && <CheckCircle2 className="inline h-4 w-4 text-violet-600 ml-1" />}
              </button>
            ))}
          </div>
        </div>
      )}
      <label className="block text-sm font-medium text-gray-700">Select a learning game</label>
      {loading ? (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading your games&hellip;
        </div>
      ) : loadError ? (
        <div className="flex items-center gap-2 text-sm text-red-600">
          <AlertTriangle className="w-4 h-4" /> {loadError}
          <button
            type="button"
            onClick={refresh}
            className="ml-2 text-blue-600 hover:underline inline-flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        </div>
      ) : (
        <select
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">— Choose a published game —</option>
          {games.map((g) => (
            <option key={g.id} value={g.id}>
              {g.title} ({g.template.replace('_', ' ')}, {g.item_count} items)
            </option>
          ))}
        </select>
      )}

      {selectedGame && (
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs text-gray-500 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-600" /> Selected: {selectedGame.title}{' '}
            ({selectedGame.template.replace('_', ' ')}, {selectedGame.item_count} items)
          </p>
          <button
            type="button"
            onClick={() => setPreviewOpen(true)}
            className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 hover:underline shrink-0"
          >
            <Eye className="w-3.5 h-3.5" /> Preview
          </button>
        </div>
      )}

      <Link
        to="/instructor/games"
        className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:underline"
      >
        <Gamepad2 className="w-3.5 h-3.5" /> Create new game &rarr;
      </Link>

      {previewOpen && selectedGame && (
        <div
          className="fixed inset-0 z-[100] bg-black/70 flex items-center justify-center p-4"
          onClick={() => setPreviewOpen(false)}
        >
          <div
            className="bg-white rounded-2xl max-w-3xl w-full overflow-hidden shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
              <p className="font-semibold text-gray-900">{selectedGame.title}</p>
              <button
                type="button"
                onClick={() => setPreviewOpen(false)}
                aria-label="Close preview"
                className="text-gray-400 hover:text-gray-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="bg-neutral-950" style={{ height: '70vh' }}>
              {/* previewOnly: mirrors H5PPicker/H5PLesson — an instructor
                  play-through must never write an advisory result or mark a
                  real lesson complete. */}
              <GamePlayer gameId={selectedGame.id} previewOnly />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default GamePicker
