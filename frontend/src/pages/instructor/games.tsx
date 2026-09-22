import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Instructor games library — template gallery (Create -> builder) + a table
 * of the instructor's own games (Task 10). No page-level shell: renders
 * inside InstructorLayout, matching certificate-designer.tsx / gradebook.tsx
 * conventions. All instructor-authored strings (titles) render as React
 * text only — no dangerouslySetInnerHTML anywhere in games code.
 */
import * as React from "react";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import {
  Trash2,
  Pencil,
  Upload,
  Download,
  BarChart3,
  X,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  listMyGames,
  publishGame,
  unpublishGame,
  deleteGame,
  listGameResults,
  type GameSummary,
  type GameTemplate,
  type RollupRow,
} from "@/api/games";

interface TemplateMeta {
  key: GameTemplate;
  name: string;
  description: string;
  accent: string; // tailwind text/bg color pair prefix, e.g. 'violet'
  illustration: React.ReactNode;
}

const ACCENT_CLASSES: Record<
  string,
  { bg: string; text: string; ring: string }
> = {
  violet: {
    bg: "bg-violet-50",
    text: "text-violet-600",
    ring: "ring-violet-200",
  },
  emerald: {
    bg: "bg-emerald-50",
    text: "text-emerald-600",
    ring: "ring-emerald-200",
  },
  amber: { bg: "bg-amber-50", text: "text-amber-600", ring: "ring-amber-200" },
  sky: { bg: "bg-sky-50", text: "text-sky-600", ring: "ring-sky-200" },
  rose: { bg: "bg-rose-50", text: "text-rose-600", ring: "ring-rose-200" },
};

const TEMPLATES: TemplateMeta[] = [
  {
    key: "quiz_rush",
    name: "Quiz Rush",
    description:
      "Timed multiple-choice race — faster correct answers score more.",
    accent: "violet",
    illustration: (
      <svg viewBox="0 0 64 64" className="w-full h-full" aria-hidden>
        <circle
          cx="32"
          cy="32"
          r="26"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          opacity="0.25"
        />
        <path
          d="M32 14v18l12 8"
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
  {
    key: "match_pairs",
    name: "Match Pairs",
    description:
      "Flip-card matching — pair up related concepts as fast as you can.",
    accent: "emerald",
    illustration: (
      <svg viewBox="0 0 64 64" className="w-full h-full" aria-hidden>
        <rect
          x="8"
          y="16"
          width="18"
          height="26"
          rx="3"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
        />
        <rect
          x="38"
          y="16"
          width="18"
          height="26"
          rx="3"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
        />
        <path
          d="M26 29h12"
          stroke="currentColor"
          strokeWidth="3"
          strokeDasharray="3 3"
        />
      </svg>
    ),
  },
  {
    key: "drag_sort",
    name: "Drag Sort",
    description: "Drag items into the right category bucket.",
    accent: "amber",
    illustration: (
      <svg viewBox="0 0 64 64" className="w-full h-full" aria-hidden>
        <rect
          x="6"
          y="38"
          width="22"
          height="18"
          rx="3"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
        />
        <rect
          x="36"
          y="38"
          width="22"
          height="18"
          rx="3"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
        />
        <rect
          x="24"
          y="8"
          width="16"
          height="16"
          rx="3"
          fill="currentColor"
          opacity="0.3"
        />
      </svg>
    ),
  },
  {
    key: "word_builder",
    name: "Word Builder",
    description: "Spell the answer to a clue by tapping letter tiles.",
    accent: "sky",
    illustration: (
      <svg viewBox="0 0 64 64" className="w-full h-full" aria-hidden>
        <rect
          x="6"
          y="24"
          width="12"
          height="14"
          rx="2"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
        />
        <rect
          x="22"
          y="24"
          width="12"
          height="14"
          rx="2"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
        />
        <rect
          x="38"
          y="24"
          width="12"
          height="14"
          rx="2"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
        />
        <path
          d="M12 44l6 6 6-6"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
  {
    key: "sequence",
    name: "Sequence",
    description: "Drag steps into the correct order.",
    accent: "rose",
    illustration: (
      <svg viewBox="0 0 64 64" className="w-full h-full" aria-hidden>
        <path
          d="M10 16h44M10 32h44M10 48h30"
          stroke="currentColor"
          strokeWidth="4"
          strokeLinecap="round"
        />
        <circle cx="6" cy="16" r="3" fill="currentColor" />
        <circle cx="6" cy="32" r="3" fill="currentColor" />
        <circle cx="6" cy="48" r="3" fill="currentColor" />
      </svg>
    ),
  },
];

function errorDetail(err: any, fallback: string): string {
  return err?.response?.data?.detail || err?.message || fallback;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

function ResultsDrawer({
  game,
  onClose,
}: {
  game: GameSummary;
  onClose: () => void;
}) {
  const [rows, setRows] = React.useState<RollupRow[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listGameResults(game.id)
      .then((data) => {
        if (cancelled) return;
        setRows(data.results);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(errorDetail(err, "Failed to load results"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [game.id]);

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden shadow-2xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
        data-glass="work"
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 shrink-0">
          <p className="font-semibold text-gray-900">Results — {game.title}</p>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close results"
            className="text-gray-400 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-gray-500 py-8 justify-center">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading
              results&hellip;
            </div>
          ) : error ? (
            <p className="text-sm text-danger-600 text-center py-8">{error}</p>
          ) : !rows || rows.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">
              No students have played this game yet.
            </p>
          ) : (
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-100">
                  <th className="py-2 pr-4 font-medium">Student</th>
                  <th className="py-2 pr-4 font-medium">Best score</th>
                  <th className="py-2 pr-4 font-medium">Attempts</th>
                  <th className="py-2 font-medium">Last played</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.user_id} className="border-b border-gray-50">
                    <td className="py-2 pr-4 text-gray-900">{row.user_name}</td>
                    <td className="py-2 pr-4 tabular-nums">
                      {row.best_score} / {row.max_score}
                    </td>
                    <td className="py-2 pr-4 tabular-nums">{row.attempts}</td>
                    <td className="py-2 text-gray-500">
                      {formatDate(row.last_played)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export default function InstructorGamesPage() {
  const navigate = useNavigate();
  const [games, setGames] = React.useState<GameSummary[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [busyId, setBusyId] = React.useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = React.useState<number | null>(
    null,
  );
  const [resultsGame, setResultsGame] = React.useState<GameSummary | null>(
    null,
  );

  const load = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listMyGames();
      setGames(data.games);
    } catch (err) {
      setError(errorDetail(err, "Failed to load your games"));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  const handleTogglePublish = async (game: GameSummary) => {
    setBusyId(game.id);
    try {
      const updated =
        game.status === "published"
          ? await unpublishGame(game.id)
          : await publishGame(game.id);
      setGames((prev) =>
        prev.map((g) =>
          g.id === game.id ? { ...g, status: updated.status } : g,
        ),
      );
      toast.success(
        updated.status === "published" ? "Game published" : "Game unpublished",
      );
    } catch (err) {
      // 409s (e.g. attached-lesson conflicts) carry a human-readable detail —
      // surface it verbatim rather than a generic message.
      toast.error(errorDetail(err, "Failed to update game status"));
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (game: GameSummary) => {
    setBusyId(game.id);
    try {
      await deleteGame(game.id);
      setGames((prev) => prev.filter((g) => g.id !== game.id));
      toast.success("Game deleted");
    } catch (err) {
      toast.error(errorDetail(err, "Failed to delete game"));
    } finally {
      setBusyId(null);
      setConfirmDeleteId(null);
    }
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <h1 className="dash-h1 mb-1">Games</h1>
          <p className="text-slate-600 text-sm">
            Build interactive learning games and attach them to your course
            lessons.
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-games"
    >
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-slate-700 mb-3">
          Start from a template
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {TEMPLATES.map((tpl) => {
            const accent = ACCENT_CLASSES[tpl.accent];
            return (
              <Card key={tpl.key} hover className="p-4 flex flex-col">
                <div
                  className={`w-14 h-14 rounded-xl ${accent.bg} ${accent.text} p-3 mb-3`}
                >
                  {tpl.illustration}
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">{tpl.name}</h3>
                <p className="text-xs text-gray-500 mb-4 flex-1">
                  {tpl.description}
                </p>
                <Link to={`/instructor/games/new?template=${tpl.key}`}>
                  <Button size="sm" className="w-full">
                    Create
                  </Button>
                </Link>
              </Card>
            );
          })}
        </div>
      </section>
      <section>
        <h2 className="text-sm font-semibold text-slate-700 mb-3">
          Your games
        </h2>
        {loading ? (
          <Card className="p-8">
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-10 w-full dash-skeleton" />
              ))}
            </div>
          </Card>
        ) : error ? (
          <Card className="p-8 text-center">
            <p className="text-sm text-danger-600 mb-3">{error}</p>
            <Button variant="outline" onClick={load}>
              Try again
            </Button>
          </Card>
        ) : games.length === 0 ? (
          <Card className="p-12 text-center">
            <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No games yet
            </h3>
            <p className="text-gray-600">
              Pick a template above to create your first game.
            </p>
          </Card>
        ) : (
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="text-left px-4 py-3 font-semibold text-slate-700">
                      Title
                    </th>
                    <th className="text-left px-4 py-3 font-semibold text-slate-700">
                      Template
                    </th>
                    <th className="text-left px-4 py-3 font-semibold text-slate-700">
                      Status
                    </th>
                    <th className="text-left px-4 py-3 font-semibold text-slate-700">
                      Items
                    </th>
                    <th className="text-left px-4 py-3 font-semibold text-slate-700">
                      Lessons
                    </th>
                    <th className="text-left px-4 py-3 font-semibold text-slate-700">
                      Updated
                    </th>
                    <th className="text-right px-4 py-3 font-semibold text-slate-700">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {games.map((game) => (
                    <tr
                      key={game.id}
                      className="border-b border-slate-100 hover:bg-slate-50/60"
                    >
                      <td className="px-4 py-3 font-medium text-slate-900">
                        {game.title}
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {TEMPLATES.find((t) => t.key === game.template)?.name ??
                          game.template}
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          variant={
                            game.status === "published" ? "success" : "neutral"
                          }
                        >
                          {game.status === "published" ? "Published" : "Draft"}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 tabular-nums text-slate-600">
                        {game.item_count}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-slate-600">
                        {game.attached_lesson_count}
                      </td>
                      <td className="px-4 py-3 text-slate-500">
                        {formatDate(game.updated_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1.5 flex-wrap">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() =>
                              navigate(`/instructor/games/${game.id}/edit`)
                            }
                            title="Edit"
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setResultsGame(game)}
                            title="Results"
                          >
                            <BarChart3 className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={busyId === game.id}
                            onClick={() => handleTogglePublish(game)}
                            title={
                              game.status === "published"
                                ? "Unpublish"
                                : "Publish"
                            }
                          >
                            {game.status === "published" ? (
                              <Download className="w-4 h-4" />
                            ) : (
                              <Upload className="w-4 h-4" />
                            )}
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            disabled={busyId === game.id}
                            onClick={() => setConfirmDeleteId(game.id)}
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </section>
      {confirmDeleteId != null && (
        <div
          className="fixed inset-0 z-[100] bg-black/50 flex items-center justify-center p-4"
          onClick={() => setConfirmDeleteId(null)}
        >
          <div
            className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
            data-glass="content"
          >
            <div className="flex items-center gap-2 text-amber-600 mb-3">
              <AlertTriangle className="w-5 h-5" />
              <p className="font-semibold text-gray-900">Delete this game?</p>
            </div>
            <p className="text-sm text-gray-600 mb-5">
              This permanently deletes the game and cannot be undone. Games
              attached to a lesson may not be deletable.
            </p>
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setConfirmDeleteId(null)}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                disabled={busyId === confirmDeleteId}
                onClick={() => {
                  const game = games.find((g) => g.id === confirmDeleteId);
                  if (game) handleDelete(game);
                }}
              >
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}
      {resultsGame && (
        <ResultsDrawer
          game={resultsGame}
          onClose={() => setResultsGame(null)}
        />
      )}
    </PageLayout>
  );
}
