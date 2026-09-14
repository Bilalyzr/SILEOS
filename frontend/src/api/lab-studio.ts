import { api } from "./axios";

export type LabEngine =
  | "supplied"
  | "linear"
  | "projectile"
  | "pendulum"
  | "circuit"
  | "gas"
  | "wave"
  | "classification";
export interface ConceptConfig {
  source_slug?: string | null;
  hotspots?: LabHotspot[];
  guided_steps?: LabStep[];
  assessment_enabled?: boolean;
  concepts?: string[];
  model_description?: string;
  model_description_ta?: string;
  model_id?: number | null;
  engine: LabEngine;
  objective: string;
  prediction: string;
  investigation: string[];
  explanation: string;
  chapter_ids: string[];
  cards: { label: string; group: string; explanation: string }[];
}
export interface LabHotspot {
  id: string;
  label: string;
  label_ta?: string;
  explanation: string;
  explanation_ta?: string;
  position: number[];
}
export interface LabStep {
  id: string;
  kind: "visit" | "parameter" | "question" | "observation";
  title: string;
  title_ta?: string;
  instruction: string;
  instruction_ta?: string;
  hotspot_id?: string | null;
  parameter?: "rotation_y" | "scale" | "explode" | null;
  target_min?: number;
  target_max?: number;
  options: string[];
  correct_index?: number | null;
  points: number;
}
export interface LabDraft {
  slug: string;
  title: string;
  subject: string;
  description: string;
  config: ConceptConfig;
  is_published: boolean;
}
export type LabDraftInput = Pick<
  LabDraft,
  "title" | "subject" | "description" | "config"
>;
export interface Chapter {
  id: string;
  edition?: string;
  grade: number;
  subject: string;
  title: string;
  difficulty: number;
  lab_slug: string | null;
  activity_kind?: "classification";
}
export interface BundledLab {
  slug: string;
  title: string;
  subject: string;
  description: string;
  grades: number[];
  embed_url: string;
  spatial: "scene" | "panel";
}
export interface Curriculum {
  editions?: { id: string; label: string }[];
  chapters: Chapter[];
  labs: BundledLab[];
  source: string;
}
export type Trial = Record<string, string | number | boolean>;
export interface Notebook {
  prediction: string;
  observation: string;
  conclusion: string;
  trials: Trial[];
}
export const blankNotebook = (): Notebook => ({
  prediction: "",
  observation: "",
  conclusion: "",
  trials: [],
});
export const labStudio = {
  curriculum: async () =>
    (await api.get<Curriculum>("/lab-studio/curriculum")).data,
  drafts: async () =>
    (await api.get<{ labs: LabDraft[] }>("/lab-studio/drafts")).data.labs,
  create: async (draft: LabDraftInput) =>
    (await api.post<LabDraft>("/lab-studio/drafts", draft)).data,
  update: async (slug: string, draft: LabDraftInput) =>
    (
      await api.put<LabDraft>(
        `/lab-studio/drafts/${encodeURIComponent(slug)}`,
        draft,
      )
    ).data,
  publish: async (slug: string, published: boolean) =>
    (
      await api.post<LabDraft>(
        `/lab-studio/drafts/${encodeURIComponent(slug)}/publication`,
        { published },
      )
    ).data,
  import: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return (await api.post<{ labs: LabDraft[] }>("/lab-studio/import", form))
      .data.labs;
  },
  export: async (slug: string) =>
    (
      await api.get<Blob>(
        `/lab-studio/drafts/${encodeURIComponent(slug)}/export`,
        { responseType: "blob" },
      )
    ).data,
  notebook: async (slug: string) =>
    (
      await api.get<Notebook>(
        `/lab-studio/notebooks/${encodeURIComponent(slug)}`,
      )
    ).data,
  saveNotebook: async (slug: string, notebook: Notebook) =>
    (
      await api.put(
        `/lab-studio/notebooks/${encodeURIComponent(slug)}`,
        notebook,
      )
    ).data,
};

export function downloadLabFile(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
