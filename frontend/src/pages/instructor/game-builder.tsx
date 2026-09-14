import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Instructor game builder — create/edit a game's title + per-template
 * config with inline validation and a LIVE PREVIEW that runs the real
 * engine components directly against the local unsaved draft (previewOnly
 * semantics: no network, no result POST — the POST lives only in
 * GamePlayer). Routes: /instructor/games/new?template=X (create) and
 * /instructor/games/:id/edit (edit, via getGame). No page-level shell:
 * renders inside InstructorLayout. All instructor-authored config strings
 * render as React text only — no dangerouslySetInnerHTML anywhere in games
 * code.
 */
import * as React from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import {
  ArrowLeft,
  Plus,
  Trash2,
  ChevronUp,
  ChevronDown,
  RotateCcw,
  Loader2,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  createGame,
  getGame,
  updateGame,
  publishGame,
  type Game,
  type GameConfig,
  type GameTemplate,
  type QuizRushConfig,
  type MatchPairsConfig,
  type DragSortConfig,
  type WordBuilderConfig,
  type SequenceConfig,
} from "@/api/games";
import {
  validateConfigDraft,
  duplicateWarnings,
  MAX_ITEM_STRING,
  MAX_OPTION_STRING,
} from "@/components/games/builderValidation";
import { QuizRush } from "@/components/games/engines/QuizRush";
import { MatchPairs } from "@/components/games/engines/MatchPairs";
import { DragSort } from "@/components/games/engines/DragSort";
import { WordBuilder } from "@/components/games/engines/WordBuilder";
import { SequenceGame } from "@/components/games/engines/SequenceGame";

const TEMPLATE_NAMES: Record<GameTemplate, string> = {
  quiz_rush: "Quiz Rush",
  match_pairs: "Match Pairs",
  drag_sort: "Drag Sort",
  word_builder: "Word Builder",
  sequence: "Sequence",
};

function errorDetail(err: any, fallback: string): string {
  return err?.response?.data?.detail || err?.message || fallback;
}

function emptyConfig(template: GameTemplate): GameConfig {
  switch (template) {
    case "quiz_rush":
      return {
        items: [{ prompt: "", options: ["", ""], answer_index: 0 }],
        settings: { seconds_per_question: 20, shuffle: false },
      } satisfies QuizRushConfig;
    case "match_pairs":
      return {
        items: [
          { left: "", right: "" },
          { left: "", right: "" },
          { left: "", right: "" },
        ],
        settings: { time_limit_s: 0 },
      } satisfies MatchPairsConfig;
    case "drag_sort":
      return {
        categories: [{ name: "" }, { name: "" }],
        items: [
          { text: "", category_index: 0 },
          { text: "", category_index: 0 },
          { text: "", category_index: 1 },
          { text: "", category_index: 1 },
        ],
        settings: { time_limit_s: 0 },
      } satisfies DragSortConfig;
    case "word_builder":
      return {
        items: [{ clue: "", answer: "" }],
        settings: { hints_allowed: 1 },
      } satisfies WordBuilderConfig;
    case "sequence":
      return {
        items: [{ text: "" }, { text: "" }, { text: "" }],
        settings: { time_limit_s: 0, shuffle: true },
      } satisfies SequenceConfig;
  }
}

function moveItem<T>(arr: T[], index: number, dir: -1 | 1): T[] {
  const target = index + dir;
  if (target < 0 || target >= arr.length) return arr;
  const copy = [...arr];
  [copy[index], copy[target]] = [copy[target], copy[index]];
  return copy;
}

function RemainingHint({ value, max }: { value: string; max: number }) {
  const remaining = max - value.length;
  if (remaining > 40) return null;
  return (
    <span
      className={`text-[11px] ${remaining < 0 ? "text-danger-600" : "text-gray-400"}`}
    >
      {remaining} left
    </span>
  );
}

// ---- per-template item editors ------------------------------------------

function QuizRushEditor({
  config,
  onChange,
}: {
  config: QuizRushConfig;
  onChange: (c: QuizRushConfig) => void;
}) {
  const setItem = (
    i: number,
    patch: Partial<QuizRushConfig["items"][number]>,
  ) => {
    const items = config.items.map((it, idx) =>
      idx === i ? { ...it, ...patch } : it,
    );
    onChange({ ...config, items });
  };
  const addItem = () => {
    if (config.items.length >= 50) return;
    onChange({
      ...config,
      items: [
        ...config.items,
        { prompt: "", options: ["", ""], answer_index: 0 },
      ],
    });
  };
  const removeItem = (i: number) => {
    onChange({ ...config, items: config.items.filter((_, idx) => idx !== i) });
  };
  const moveQ = (i: number, dir: -1 | 1) =>
    onChange({ ...config, items: moveItem(config.items, i, dir) });

  return (
    <div className="space-y-4">
      {config.items.map((item, i) => (
        <Card key={i} className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-gray-700">
              Question {i + 1}
            </p>
            <div className="flex items-center gap-1">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => moveQ(i, -1)}
                disabled={i === 0}
                aria-label="Move up"
              >
                <ChevronUp className="w-4 h-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => moveQ(i, 1)}
                disabled={i === config.items.length - 1}
                aria-label="Move down"
              >
                <ChevronDown className="w-4 h-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => removeItem(i)}
                disabled={config.items.length <= 1}
                aria-label="Remove question"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </div>
          <div>
            <input
              value={item.prompt}
              onChange={(e) => setItem(i, { prompt: e.target.value })}
              placeholder="Question prompt"
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded"
            />
            <RemainingHint value={item.prompt} max={MAX_ITEM_STRING} />
          </div>
          <div className="space-y-2">
            {item.options.map((opt, oi) => (
              <div key={oi} className="flex items-center gap-2">
                <input
                  type="radio"
                  name={`quiz-correct-${i}`}
                  checked={item.answer_index === oi}
                  onChange={() => setItem(i, { answer_index: oi })}
                  aria-label={`Option ${oi + 1} is correct`}
                />
                <input
                  value={opt}
                  onChange={(e) =>
                    setItem(i, {
                      options: item.options.map((o, k) =>
                        k === oi ? e.target.value : o,
                      ),
                    })
                  }
                  placeholder={`Option ${oi + 1}`}
                  className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded"
                />
                <RemainingHint value={opt} max={MAX_OPTION_STRING} />
                <button
                  type="button"
                  onClick={() =>
                    setItem(i, {
                      options: item.options.filter((_, k) => k !== oi),
                      answer_index:
                        item.answer_index >= oi && item.answer_index > 0
                          ? item.answer_index - 1
                          : item.answer_index,
                    })
                  }
                  disabled={item.options.length <= 2}
                  className="text-gray-400 hover:text-danger-600 disabled:opacity-30"
                  aria-label="Remove option"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setItem(i, { options: [...item.options, ""] })}
              disabled={item.options.length >= 6}
            >
              <Plus className="w-3.5 h-3.5 mr-1" /> Add option
            </Button>
          </div>
        </Card>
      ))}
      <Button
        variant="outline"
        onClick={addItem}
        disabled={config.items.length >= 50}
      >
        <Plus className="w-4 h-4 mr-1" /> Add question
      </Button>

      <Card className="p-4 space-y-3">
        <p className="text-sm font-semibold text-gray-700">Settings</p>
        <label className="block text-sm">
          Seconds per question (5-120)
          <input
            type="number"
            min={5}
            max={120}
            value={config.settings.seconds_per_question}
            onChange={(e) =>
              onChange({
                ...config,
                settings: {
                  ...config.settings,
                  seconds_per_question: Number(e.target.value),
                },
              })
            }
            className="mt-1 w-full px-3 py-2 text-sm border border-gray-300 rounded"
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={config.settings.shuffle}
            onChange={(e) =>
              onChange({
                ...config,
                settings: { ...config.settings, shuffle: e.target.checked },
              })
            }
          />
          Shuffle question order
        </label>
      </Card>
    </div>
  );
}

function MatchPairsEditor({
  config,
  onChange,
}: {
  config: MatchPairsConfig;
  onChange: (c: MatchPairsConfig) => void;
}) {
  const setItem = (
    i: number,
    patch: Partial<MatchPairsConfig["items"][number]>,
  ) => {
    onChange({
      ...config,
      items: config.items.map((it, idx) =>
        idx === i ? { ...it, ...patch } : it,
      ),
    });
  };
  const addItem = () => {
    if (config.items.length >= 12) return;
    onChange({ ...config, items: [...config.items, { left: "", right: "" }] });
  };
  const removeItem = (i: number) =>
    onChange({ ...config, items: config.items.filter((_, idx) => idx !== i) });
  const moveQ = (i: number, dir: -1 | 1) =>
    onChange({ ...config, items: moveItem(config.items, i, dir) });

  return (
    <div className="space-y-4">
      {config.items.map((item, i) => (
        <div key={i} className="flex items-center gap-2">
          <input
            value={item.left}
            onChange={(e) => setItem(i, { left: e.target.value })}
            placeholder={`Pair ${i + 1} — left`}
            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded"
          />
          <input
            value={item.right}
            onChange={(e) => setItem(i, { right: e.target.value })}
            placeholder={`Pair ${i + 1} — right`}
            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded"
          />
          <Button
            size="sm"
            variant="ghost"
            onClick={() => moveQ(i, -1)}
            disabled={i === 0}
            aria-label="Move up"
          >
            <ChevronUp className="w-4 h-4" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => moveQ(i, 1)}
            disabled={i === config.items.length - 1}
            aria-label="Move down"
          >
            <ChevronDown className="w-4 h-4" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => removeItem(i)}
            disabled={config.items.length <= 3}
            aria-label="Remove pair"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      ))}
      <Button
        variant="outline"
        onClick={addItem}
        disabled={config.items.length >= 12}
      >
        <Plus className="w-4 h-4 mr-1" /> Add pair
      </Button>

      <Card className="p-4">
        <label className="block text-sm">
          Time limit in seconds (0 = off, up to 600)
          <input
            type="number"
            min={0}
            max={600}
            value={config.settings.time_limit_s}
            onChange={(e) =>
              onChange({
                ...config,
                settings: { time_limit_s: Number(e.target.value) },
              })
            }
            className="mt-1 w-full px-3 py-2 text-sm border border-gray-300 rounded"
          />
        </label>
      </Card>
    </div>
  );
}

function DragSortEditor({
  config,
  onChange,
}: {
  config: DragSortConfig;
  onChange: (c: DragSortConfig) => void;
}) {
  const setCategory = (i: number, name: string) => {
    onChange({
      ...config,
      categories: config.categories.map((c, idx) => (idx === i ? { name } : c)),
    });
  };
  const addCategory = () => {
    if (config.categories.length >= 5) return;
    onChange({ ...config, categories: [...config.categories, { name: "" }] });
  };
  const removeCategory = (i: number) => {
    // Re-point items that pointed at the removed category (and shift indices above it).
    const items = config.items
      .filter((it) => it.category_index !== i)
      .map((it) => ({
        ...it,
        category_index:
          it.category_index > i ? it.category_index - 1 : it.category_index,
      }));
    onChange({
      ...config,
      categories: config.categories.filter((_, idx) => idx !== i),
      items,
    });
  };

  const setItem = (
    i: number,
    patch: Partial<DragSortConfig["items"][number]>,
  ) => {
    onChange({
      ...config,
      items: config.items.map((it, idx) =>
        idx === i ? { ...it, ...patch } : it,
      ),
    });
  };
  const addItem = () => {
    if (config.items.length >= 40) return;
    onChange({
      ...config,
      items: [...config.items, { text: "", category_index: 0 }],
    });
  };
  const removeItem = (i: number) =>
    onChange({ ...config, items: config.items.filter((_, idx) => idx !== i) });
  const moveQ = (i: number, dir: -1 | 1) =>
    onChange({ ...config, items: moveItem(config.items, i, dir) });

  return (
    <div className="space-y-4">
      <Card className="p-4 space-y-2">
        <p className="text-sm font-semibold text-gray-700">Categories</p>
        {config.categories.map((cat, i) => (
          <div key={i} className="flex items-center gap-2">
            <input
              value={cat.name}
              onChange={(e) => setCategory(i, e.target.value)}
              placeholder={`Category ${i + 1} name`}
              className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded"
            />
            <Button
              size="sm"
              variant="ghost"
              onClick={() => removeCategory(i)}
              disabled={config.categories.length <= 2}
              aria-label="Remove category"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        ))}
        <Button
          size="sm"
          variant="outline"
          onClick={addCategory}
          disabled={config.categories.length >= 5}
        >
          <Plus className="w-3.5 h-3.5 mr-1" /> Add category
        </Button>
      </Card>

      <div className="space-y-2">
        {config.items.map((item, i) => (
          <div key={i} className="flex items-center gap-2">
            <input
              value={item.text}
              onChange={(e) => setItem(i, { text: e.target.value })}
              placeholder={`Item ${i + 1}`}
              className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded"
            />
            <select
              value={item.category_index}
              onChange={(e) =>
                setItem(i, { category_index: Number(e.target.value) })
              }
              className="px-2 py-2 text-sm border border-gray-300 rounded"
            >
              {config.categories.map((cat, ci) => (
                <option key={ci} value={ci}>
                  {cat.name || `Category ${ci + 1}`}
                </option>
              ))}
            </select>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => moveQ(i, -1)}
              disabled={i === 0}
              aria-label="Move up"
            >
              <ChevronUp className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => moveQ(i, 1)}
              disabled={i === config.items.length - 1}
              aria-label="Move down"
            >
              <ChevronDown className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => removeItem(i)}
              disabled={config.items.length <= 4}
              aria-label="Remove item"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        ))}
        <Button
          variant="outline"
          onClick={addItem}
          disabled={config.items.length >= 40}
        >
          <Plus className="w-4 h-4 mr-1" /> Add item
        </Button>
      </div>

      <Card className="p-4">
        <label className="block text-sm">
          Time limit in seconds (0 = off, up to 600)
          <input
            type="number"
            min={0}
            max={600}
            value={config.settings.time_limit_s}
            onChange={(e) =>
              onChange({
                ...config,
                settings: { time_limit_s: Number(e.target.value) },
              })
            }
            className="mt-1 w-full px-3 py-2 text-sm border border-gray-300 rounded"
          />
        </label>
      </Card>
    </div>
  );
}

function WordBuilderEditor({
  config,
  onChange,
}: {
  config: WordBuilderConfig;
  onChange: (c: WordBuilderConfig) => void;
}) {
  const setItem = (
    i: number,
    patch: Partial<WordBuilderConfig["items"][number]>,
  ) => {
    onChange({
      ...config,
      items: config.items.map((it, idx) =>
        idx === i ? { ...it, ...patch } : it,
      ),
    });
  };
  const addItem = () => {
    if (config.items.length >= 20) return;
    onChange({ ...config, items: [...config.items, { clue: "", answer: "" }] });
  };
  const removeItem = (i: number) =>
    onChange({ ...config, items: config.items.filter((_, idx) => idx !== i) });
  const moveQ = (i: number, dir: -1 | 1) =>
    onChange({ ...config, items: moveItem(config.items, i, dir) });

  return (
    <div className="space-y-4">
      {config.items.map((item, i) => (
        <Card key={i} className="p-4 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-gray-700">Word {i + 1}</p>
            <div className="flex items-center gap-1">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => moveQ(i, -1)}
                disabled={i === 0}
                aria-label="Move up"
              >
                <ChevronUp className="w-4 h-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => moveQ(i, 1)}
                disabled={i === config.items.length - 1}
                aria-label="Move down"
              >
                <ChevronDown className="w-4 h-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => removeItem(i)}
                disabled={config.items.length <= 1}
                aria-label="Remove word"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </div>
          <input
            value={item.clue}
            onChange={(e) => setItem(i, { clue: e.target.value })}
            placeholder="Clue"
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded"
          />
          <input
            value={item.answer}
            onChange={(e) => setItem(i, { answer: e.target.value })}
            placeholder="Answer (letters, digits, spaces — 2-24 chars)"
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded"
          />
        </Card>
      ))}
      <Button
        variant="outline"
        onClick={addItem}
        disabled={config.items.length >= 20}
      >
        <Plus className="w-4 h-4 mr-1" /> Add word
      </Button>

      <Card className="p-4">
        <label className="block text-sm">
          Hints allowed (0-3)
          <input
            type="number"
            min={0}
            max={3}
            value={config.settings.hints_allowed}
            onChange={(e) =>
              onChange({
                ...config,
                settings: { hints_allowed: Number(e.target.value) },
              })
            }
            className="mt-1 w-full px-3 py-2 text-sm border border-gray-300 rounded"
          />
        </label>
      </Card>
    </div>
  );
}

function SequenceEditor({
  config,
  onChange,
}: {
  config: SequenceConfig;
  onChange: (c: SequenceConfig) => void;
}) {
  const setItem = (i: number, text: string) => {
    onChange({
      ...config,
      items: config.items.map((it, idx) => (idx === i ? { text } : it)),
    });
  };
  const addItem = () => {
    if (config.items.length >= 10) return;
    onChange({ ...config, items: [...config.items, { text: "" }] });
  };
  const removeItem = (i: number) =>
    onChange({ ...config, items: config.items.filter((_, idx) => idx !== i) });
  const moveQ = (i: number, dir: -1 | 1) =>
    onChange({ ...config, items: moveItem(config.items, i, dir) });

  return (
    <div className="space-y-4">
      <p className="text-xs text-gray-500">
        Enter the steps in their correct order — this order is the answer key.
      </p>
      {config.items.map((item, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="text-sm text-gray-400 w-5 tabular-nums">
            {i + 1}.
          </span>
          <input
            value={item.text}
            onChange={(e) => setItem(i, e.target.value)}
            placeholder={`Step ${i + 1}`}
            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded"
          />
          <Button
            size="sm"
            variant="ghost"
            onClick={() => moveQ(i, -1)}
            disabled={i === 0}
            aria-label="Move up"
          >
            <ChevronUp className="w-4 h-4" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => moveQ(i, 1)}
            disabled={i === config.items.length - 1}
            aria-label="Move down"
          >
            <ChevronDown className="w-4 h-4" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => removeItem(i)}
            disabled={config.items.length <= 3}
            aria-label="Remove step"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      ))}
      <Button
        variant="outline"
        onClick={addItem}
        disabled={config.items.length >= 10}
      >
        <Plus className="w-4 h-4 mr-1" /> Add step
      </Button>

      <Card className="p-4">
        <label className="block text-sm">
          Time limit in seconds (0 = off, up to 600)
          <input
            type="number"
            min={0}
            max={600}
            value={config.settings.time_limit_s}
            onChange={(e) =>
              onChange({
                ...config,
                settings: {
                  ...config.settings,
                  time_limit_s: Number(e.target.value),
                },
              })
            }
            className="mt-1 w-full px-3 py-2 text-sm border border-gray-300 rounded"
          />
        </label>
        <p className="text-xs text-gray-400 mt-2">
          Items are always shuffled before play.
        </p>
      </Card>
    </div>
  );
}

// ---- live preview ---------------------------------------------------------

function LivePreview({
  template,
  config,
  previewNonce,
}: {
  template: GameTemplate;
  config: GameConfig;
  previewNonce: number;
}) {
  const noop = () => {};
  return (
    <div key={previewNonce} className="h-full">
      {template === "quiz_rush" && (
        <QuizRush
          config={config as QuizRushConfig}
          onComplete={noop}
          title="Preview"
        />
      )}
      {template === "match_pairs" && (
        <MatchPairs
          config={config as MatchPairsConfig}
          onComplete={noop}
          title="Preview"
        />
      )}
      {template === "drag_sort" && (
        <DragSort
          config={config as DragSortConfig}
          onComplete={noop}
          title="Preview"
        />
      )}
      {template === "word_builder" && (
        <WordBuilder
          config={config as WordBuilderConfig}
          onComplete={noop}
          title="Preview"
        />
      )}
      {template === "sequence" && (
        <SequenceGame
          config={config as SequenceConfig}
          onComplete={noop}
          title="Preview"
        />
      )}
    </div>
  );
}

// ---- page -------------------------------------------------------------

export default function GameBuilderPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const isEdit = !!id;
  const gameId = id ? Number(id) : null;

  const [loading, setLoading] = React.useState(isEdit);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [template, setTemplate] = React.useState<GameTemplate | null>(null);
  const [title, setTitle] = React.useState("");
  const [config, setConfig] = React.useState<GameConfig | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [publishing, setPublishing] = React.useState(false);
  const [saveError, setSaveError] = React.useState<string | null>(null);
  const [previewNonce, setPreviewNonce] = React.useState(0);

  React.useEffect(() => {
    if (isEdit && gameId != null) {
      let cancelled = false;
      setLoading(true);
      setLoadError(null);
      getGame(gameId)
        .then((game: Game) => {
          if (cancelled) return;
          setTemplate(game.template);
          setTitle(game.title);
          setConfig(game.config);
        })
        .catch((err) => {
          if (cancelled) return;
          setLoadError(errorDetail(err, "Failed to load this game"));
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
      return () => {
        cancelled = true;
      };
    }
    const tplParam = searchParams.get("template") as GameTemplate | null;
    const tpl: GameTemplate =
      tplParam && tplParam in TEMPLATE_NAMES ? tplParam : "quiz_rush";
    setTemplate(tpl);
    setConfig(emptyConfig(tpl));
    setTitle("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEdit, gameId]);

  const errors =
    template && config ? validateConfigDraft(template, config) : [];
  const titleError =
    title.trim().length === 0
      ? "Title is required"
      : title.length > 200
        ? "Title must be at most 200 characters"
        : null;
  const allErrors = [...(titleError ? [titleError] : []), ...errors];
  // Non-blocking: duplicate content warnings never gate Save/Publish (ledger "Task 10: F6 RULED").
  const warnings =
    template && config ? duplicateWarnings(template, config) : [];

  const buildPayload = () => {
    if (!template || !config) return null;
    return { title: title.trim(), template, config };
  };

  const handleSave = async (): Promise<Game | null> => {
    if (!template || !config || allErrors.length > 0) return null;
    setSaving(true);
    setSaveError(null);
    try {
      let saved: Game;
      if (isEdit && gameId != null) {
        saved = await updateGame(gameId, { title: title.trim(), config });
      } else {
        const payload = buildPayload();
        if (!payload) return null;
        saved = await createGame(payload);
      }
      toast.success("Draft saved");
      if (!isEdit) {
        navigate(`/instructor/games/${saved.id}/edit`, { replace: true });
      }
      return saved;
    } catch (err) {
      const detail = errorDetail(err, "Failed to save game");
      setSaveError(detail);
      toast.error(detail);
      return null;
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    setPublishing(true);
    setSaveError(null);
    try {
      const saved = await handleSave();
      const targetId = saved?.id ?? gameId;
      if (targetId == null) return;
      await publishGame(targetId);
      toast.success("Game published");
      if (!isEdit) {
        navigate(`/instructor/games/${targetId}/edit`, { replace: true });
      }
    } catch (err) {
      const detail = errorDetail(err, "Failed to publish game");
      setSaveError(detail);
      toast.error(detail);
    } finally {
      setPublishing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-gray-500">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading game&hellip;
      </div>
    );
  }

  if (loadError) {
    return (
      <Card className="p-8 text-center">
        <p className="text-sm text-danger-600 mb-3">{loadError}</p>
        <Button variant="outline" onClick={() => navigate("/instructor/games")}>
          Back to games
        </Button>
      </Card>
    );
  }

  if (!template || !config) return null;

  return (
    <PageLayout
      header={
        <PageHeader>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/instructor/games")}
              className="btn btn-ghost btn-sm"
              aria-label="Back"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div>
              <h1 className="dash-h1 mb-1">
                {isEdit ? "Edit game" : "New game"}
              </h1>
              <div className="flex items-center gap-2">
                <p className="text-slate-600 text-sm">
                  {TEMPLATE_NAMES[template]}
                </p>
                <Badge variant="neutral">{template}</Badge>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              disabled={saving || publishing || allErrors.length > 0}
              onClick={handleSave}
            >
              {saving ? "Saving..." : "Save draft"}
            </Button>
            <Button
              disabled={saving || publishing || allErrors.length > 0}
              onClick={handlePublish}
            >
              {publishing ? "Publishing..." : "Publish"}
            </Button>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-game-builder"
    >
      {saveError && (
        <Card className="p-4 mb-4 border-danger-200 bg-danger-50">
          <p className="text-sm text-danger-700">{saveError}</p>
        </Card>
      )}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <Card className="p-4">
            <label className="block text-sm font-semibold text-gray-700">
              Title
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Game title"
                className="mt-1 w-full px-3 py-2 text-sm border border-gray-300 rounded"
              />
            </label>
          </Card>

          {template === "quiz_rush" && (
            <QuizRushEditor
              config={config as QuizRushConfig}
              onChange={(c) => setConfig(c)}
            />
          )}
          {template === "match_pairs" && (
            <MatchPairsEditor
              config={config as MatchPairsConfig}
              onChange={(c) => setConfig(c)}
            />
          )}
          {template === "drag_sort" && (
            <DragSortEditor
              config={config as DragSortConfig}
              onChange={(c) => setConfig(c)}
            />
          )}
          {template === "word_builder" && (
            <WordBuilderEditor
              config={config as WordBuilderConfig}
              onChange={(c) => setConfig(c)}
            />
          )}
          {template === "sequence" && (
            <SequenceEditor
              config={config as SequenceConfig}
              onChange={(c) => setConfig(c)}
            />
          )}

          {allErrors.length > 0 && (
            <Card className="p-4 border-danger-200 bg-danger-50">
              <p className="text-sm font-semibold text-danger-800 mb-1">
                Fix before saving:
              </p>
              <ul className="text-xs text-danger-700 list-disc list-inside space-y-0.5">
                {allErrors.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </Card>
          )}

          {warnings.length > 0 && (
            <Card className="p-4 border-amber-200 bg-amber-50">
              <p className="text-sm font-semibold text-amber-800 mb-1">
                Possible duplicates (won&apos;t block saving):
              </p>
              <ul className="text-xs text-amber-700 list-disc list-inside space-y-0.5">
                {warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </Card>
          )}
        </div>

        <div className="lg:sticky lg:top-4 self-start">
          <Card className="overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-100">
              <p className="text-sm font-semibold text-gray-700">
                Live preview
              </p>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setPreviewNonce((n) => n + 1)}
              >
                <RotateCcw className="w-3.5 h-3.5 mr-1" /> Restart preview
              </Button>
            </div>
            <div className="bg-neutral-50" style={{ minHeight: "480px" }}>
              {errors.length === 0 ? (
                <LivePreview
                  template={template}
                  config={config}
                  previewNonce={previewNonce}
                />
              ) : (
                <div className="flex items-center justify-center h-full min-h-[480px] p-6 text-center">
                  <p className="text-sm text-gray-500">
                    Fix the validation errors to see a live preview.
                  </p>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </PageLayout>
  );
}
