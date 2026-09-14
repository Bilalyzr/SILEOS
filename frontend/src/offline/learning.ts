import { api } from "@/api/axios";
import { threeDAPI } from "@/api/threeD";
import type { ConceptConfig } from "@/api/lab-studio";
import {
  all,
  ownerId,
  put,
  remove,
  type OfflinePack,
  type OfflineEvent,
} from "./storage";
let syncing: Promise<void> | null = null;
export function syncOffline() {
  if (syncing) return syncing;
  syncing = (async () => {
    const owner = ownerId();
    if (!owner || !navigator.onLine) return;
    for (const event of await all<OfflineEvent>("events")) {
      if (event.owner_id !== owner || ownerId() !== owner) continue;
      try {
        await api.post(event.path, event.body);
        await remove("events", event.key);
      } catch (e: any) {
        if (ownerId() === owner)
          await put("events", {
            ...event,
            error:
              e.response?.data?.detail ||
              "Connection unavailable. Retry when online.",
          });
      }
    }
  })().finally(() => {
    syncing = null;
  });
  return syncing;
}
export async function downloadCourse(courseId: number) {
  const owner = ownerId();
  if (!owner) throw new Error("Sign in to download enrolled courses.");
  if (!("serviceWorker" in navigator))
    throw new Error("This browser does not support offline downloads.");
  const registration =
    await navigator.serviceWorker.register("/offline-worker.js");
  if (!registration.active)
    await Promise.race([
      navigator.serviceWorker.ready,
      new Promise((_, reject) =>
        setTimeout(
          () =>
            reject(
              new Error(
                "Offline app installation timed out. Reconnect and retry.",
              ),
            ),
          45000,
        ),
      ),
    ]);
  const { data } = await api.get<OfflinePack>(
    `/lab-studio/offline/courses/${courseId}`,
  );
  if (data.owner_id !== owner)
    throw new Error("Account changed during download. Please retry.");
  const models: Record<string, Blob> = {};
  let bytes = new Blob([JSON.stringify(data)]).size;
  const ids = new Set<number>();
  for (const lesson of data.lessons) {
    if (lesson.model_id) ids.add(lesson.model_id);
    const model = (lesson.lab?.config as ConceptConfig | undefined)?.model_id;
    if (model) ids.add(model);
  }
  try {
    for (const id of ids) {
      const url = await threeDAPI.downloadUrl(id);
      try {
        const response = await fetch(url);
        models[id] = await response.blob();
        bytes += models[id].size;
        if (bytes > 150 * 1024 * 1024)
          throw new Error("This course exceeds the 150 MB offline limit.");
      } finally {
        URL.revokeObjectURL(url);
      }
    }
  } catch (e) {
    throw e instanceof Error
      ? e
      : new Error("Model download failed. No incomplete course was saved.");
  }
  const packs = await all<OfflinePack>("packs");
  const key = `${owner}:${courseId}`;
  if (
    packs
      .filter((p) => p.owner_id === owner && p.key !== key)
      .reduce((s, p) => s + p.bytes, 0) +
      bytes >
    250 * 1024 * 1024
  )
    throw new Error("Remove an older download to stay within 250 MB.");
  const pack: OfflinePack = {
    ...data,
    key,
    models,
    bytes,
    expires: Date.now() + 7 * 86400000,
  };
  await put("packs", pack);
  return pack;
}
