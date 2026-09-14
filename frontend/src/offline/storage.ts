import type { LabDetail } from "@/api/labs";
export interface OfflineLesson {
  id: number;
  title: string;
  text: string;
  revision: string;
  lab: LabDetail | null;
  model_id: number | null;
  online_media: boolean;
}
export interface OfflinePack {
  key: string;
  owner_id: number;
  course_id: number;
  title: string;
  lessons: OfflineLesson[];
  expires: number;
  models: Record<string, Blob>;
  bytes: number;
}
export interface OfflineEvent {
  key: string;
  owner_id: number;
  path: string;
  body: Record<string, unknown>;
  error?: string;
}
const database = "sasha-offline-learning";
export function ownerId(): number | null {
  try {
    return (
      JSON.parse(localStorage.getItem("auth-storage") || "{}").state?.user
        ?.id || null
    );
  } catch {
    return null;
  }
}
async function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const r = indexedDB.open(database, 1);
    r.onupgradeneeded = () => {
      r.result.createObjectStore("packs", { keyPath: "key" });
      r.result.createObjectStore("events", { keyPath: "key" });
    };
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}
export async function all<T>(store: "packs" | "events"): Promise<T[]> {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store);
    const r = tx.objectStore(store).getAll();
    tx.oncomplete = () => {
      db.close();
      resolve(r.result);
    };
    tx.onerror = () => {
      db.close();
      reject(tx.error);
    };
  });
}
export async function put(
  store: "packs" | "events",
  value: OfflinePack | OfflineEvent,
) {
  if (ownerId() !== value.owner_id)
    throw new Error("Sign in again before saving offline data.");
  const db = await open();
  return new Promise<void>((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).put(value);
    tx.oncomplete = () => {
      db.close();
      window.dispatchEvent(new Event("offline-data-changed"));
      resolve();
    };
    tx.onerror = () => {
      db.close();
      reject(tx.error);
    };
  });
}
export async function remove(store: "packs" | "events", key: string) {
  const db = await open();
  return new Promise<void>((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).delete(key);
    tx.oncomplete = () => {
      db.close();
      window.dispatchEvent(new Event("offline-data-changed"));
      resolve();
    };
    tx.onerror = () => {
      db.close();
      reject(tx.error);
    };
  });
}
export async function purgeOwner(owner: number) {
  if (typeof indexedDB === "undefined") return;
  for (const name of ["packs", "events"] as const) {
    const rows = await all<OfflinePack | OfflineEvent>(name);
    for (const row of rows)
      if (row.owner_id === owner) await remove(name, row.key);
  }
}
export async function queueEvent(path: string, body: Record<string, unknown>) {
  const owner = ownerId();
  if (!owner) throw new Error("Sign in before saving offline work.");
  const key = String(
    body.submission_id || body.event_id || crypto.randomUUID(),
  );
  await put("events", { key, owner_id: owner, path, body });
}
