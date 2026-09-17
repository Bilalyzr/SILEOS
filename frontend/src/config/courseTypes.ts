/**
 * Canonical course types — mirrors backend/app/core/course_types.py.
 * Owner ruling (2026-09-04): EVERY course belongs to exactly one of these
 * three types. Categories and tags are free-form sorting aids WITHIN a type.
 */

export interface CourseTypeOption {
  value: string
  label: string
  tamil: string
  tagline: string
  emoji: string
  cardClass: string
  selectedClass: string
}

export const COURSE_TYPES: CourseTypeOption[] = [
  {
    value: 'meiporul',
    label: 'Meiporul',
    tamil: 'மெய்ப்பொருள்',
    tagline: 'AR / VR learning',
    emoji: '🥽',
    cardClass: 'hover:border-violet-400 hover:bg-violet-50',
    selectedClass: 'border-violet-500 bg-violet-50 ring-2 ring-violet-200',
  },
  {
    value: 'seyappaduporul',
    label: 'Seyappaduporul',
    tamil: 'செயப்படுபொருள்',
    tagline: 'Skill-based training',
    emoji: '🛠️',
    cardClass: 'hover:border-emerald-400 hover:bg-emerald-50',
    selectedClass: 'border-emerald-500 bg-emerald-50 ring-2 ring-emerald-200',
  },
  {
    value: 'utporul',
    label: 'Utporul',
    tamil: 'உட்பொருள்',
    tagline: 'Tech & tools',
    emoji: '💻',
    cardClass: 'hover:border-sky-400 hover:bg-sky-50',
    selectedClass: 'border-sky-500 bg-sky-50 ring-2 ring-sky-200',
  },
]

export const COURSE_TYPE_VALUES = COURSE_TYPES.map(t => t.value)

export function courseTypeLabel(value?: string | null): string {
  if (!value) return 'Unclassified'
  const found = COURSE_TYPES.find(t => t.value === value.toLowerCase())
  return found ? `${found.label} (${found.tagline})` : value
}

export function courseTypeOption(value?: string | null): CourseTypeOption | undefined {
  if (!value) return undefined
  return COURSE_TYPES.find(t => t.value === value.toLowerCase())
}


/**
 * Tool-enablement matrix (mirrors backend app/core/course_types.py).
 * The creation wizard shows/hides tooling based on the chosen type.
 * availability "planned" renders disabled — never faked.
 */
export type CourseTool = 'virtual_labs'
  | 'video' | 'quiz' | 'games' | 'h5p' | 'geogebra'
  | 'three_d_models' | 'live_classes' | 'learning_paths' | 'rewards';

export const TOOL_LABELS: Record<CourseTool, string> = {
  virtual_labs: 'Virtual labs',
  video: 'Recorded videos',
  quiz: 'Quizzes & tests',
  games: 'Learning games',
  h5p: 'H5P interactives',
  geogebra: 'GeoGebra',
  three_d_models: '3D models (GLB)',
  live_classes: 'Live classes',
  learning_paths: 'Learning paths',
  rewards: 'Rewards & streaks',
};

export const TYPE_TOOLS: Record<string, { tools: CourseTool[]; planned: CourseTool[] }> = {
  meiporul: {
    tools: ['video', 'quiz', 'geogebra', 'h5p', 'three_d_models', 'virtual_labs', 'games', 'live_classes', 'learning_paths', 'rewards'],
    planned: [],
  },
  seyappaduporul: {
    tools: ['video', 'quiz', 'games', 'h5p', 'live_classes', 'learning_paths', 'rewards', 'virtual_labs', 'geogebra'],
    planned: ['three_d_models'],
  },
  utporul: {
    tools: ['video', 'quiz', 'games', 'h5p', 'live_classes', 'learning_paths', 'rewards', 'geogebra', 'three_d_models', 'virtual_labs'],
    planned: [],
  },
};

export function typeSupports(courseType: string | undefined, tool: CourseTool): boolean {
  if (!courseType) return true; // no type chosen yet: show nothing specialised
  const t = TYPE_TOOLS[courseType.toLowerCase()];
  return Boolean(t && t.tools.includes(tool));
}
