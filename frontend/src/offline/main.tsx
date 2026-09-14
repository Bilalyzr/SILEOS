import React, { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { ConceptLabPlayer } from "@/components/labs/ConceptLabPlayer";
import { ThreeDViewer } from "@/components/three-d/ThreeDViewer";
import {
  LearningPreferences,
  useLearningLanguage,
} from "@/components/labs/LearningPreferences";
import type { ConceptConfig } from "@/api/lab-studio";
import {
  all,
  ownerId,
  queueEvent,
  remove,
  type OfflinePack,
  type OfflineEvent,
  type OfflineLesson,
} from "./storage";
import { downloadCourse, syncOffline } from "./learning";
import "@/styles/globals.css";
import "@/styles/sasha-design.css";
import "@/styles/astra-glass.css";

function Lesson({
  lesson,
  pack,
}: {
  lesson: OfflineLesson;
  pack: OfflinePack;
}) {
  const language = useLearningLanguage(),
    ta = language === "ta";
  const [message, setMessage] = useState("");
  const modelId =
    (lesson.lab?.config as ConceptConfig)?.model_id || lesson.model_id;
  const modelBlob = modelId ? pack.models[modelId] : undefined;
  return (
    <article className="sf-surface space-y-4">
      <h2>{lesson.title}</h2>
      <div className="lesson-text">
        {lesson.text ||
          (ta
            ? "இந்தப் பாடத்தில் உரை இல்லை."
            : "This lesson has no downloadable text.")}
      </div>
      {modelId && !modelBlob ? (
        <p role="status">Preparing downloaded model…</p>
      ) : lesson.lab?.native_template === "concept_lab" ? (
        <ConceptLabPlayer
          config={lesson.lab.config as ConceptConfig}
          slug={lesson.lab.slug}
          revision={lesson.lab.revision}
          title={lesson.title}
          sourceBlob={modelBlob}
        />
      ) : lesson.lab?.embed_url?.startsWith("/labs/cbse/") ? (
        <iframe
          className="lab-frame"
          title={lesson.lab.title}
          src={lesson.lab.embed_url}
          allow="fullscreen; xr-spatial-tracking"
          allowFullScreen
          style={{ height: 680 }}
        />
      ) : modelId && modelBlob ? (
        <ThreeDViewer modelId={modelId} sourceBlob={modelBlob} enableXR />
      ) : null}
      {lesson.online_media && (
        <p>
          {ta
            ? "காணொளிகள் மற்றும் இணைப்புகளுக்கு இணையம் தேவை."
            : "Videos and linked attachments require an internet connection."}
        </p>
      )}
      <button
        className="sf-primary"
        onClick={async () => {
          try {
            await queueEvent(
              `/lab-studio/offline/courses/${pack.course_id}/lessons/${lesson.id}/complete`,
              { event_id: crypto.randomUUID(), revision: lesson.revision },
            );
            await syncOffline();
            setMessage(
              ta
                ? "பதிவு சேமிக்கப்பட்டது; இணையம் வந்ததும் ஒத்திசைக்கப்படும்."
                : "Completion saved. Queued work syncs when connected.",
            );
          } catch {
            setMessage("Unable to save completion. Sign in and retry.");
          }
        }}
      >
        {ta ? "பாடத்தை முடித்தேன்" : "Mark lesson complete"}
      </button>
      <p role="status">{message}</p>
    </article>
  );
}
function OfflineReader() {
  const language = useLearningLanguage(),
    ta = language === "ta";
  const [owner, setOwner] = useState(ownerId);
  const [lessonId, setLessonId] = useState<number | null>(null);
  const [, setClock] = useState(0);
  useEffect(() => {
    const update = () => {
      setOwner(ownerId());
      setClock((v) => v + 1);
    };
    window.addEventListener("storage", update);
    const timer = setInterval(update, 30000);
    return () => {
      window.removeEventListener("storage", update);
      clearInterval(timer);
    };
  }, []);
  const [packs, setPacks] = useState<OfflinePack[]>([]),
    [events, setEvents] = useState<OfflineEvent[]>([]),
    [selected, setSelected] = useState<string | null>(null),
    [courseId, setCourseId] = useState(
      new URLSearchParams(location.search).get("course") || "",
    ),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  const refresh = useCallback(async () => {
    setPacks(
      (await all<OfflinePack>("packs")).filter((p) => p.owner_id === ownerId()),
    );
    setEvents(
      (await all<OfflineEvent>("events")).filter(
        (e) => e.owner_id === ownerId(),
      ),
    );
  }, []);
  useEffect(() => {
    void refresh().catch(() =>
      setMessage("This browser cannot open device storage."),
    );
    const sync = () =>
      void syncOffline()
        .then(refresh)
        .catch(() => setMessage("Sync failed. Retry when connected."));
    window.addEventListener("online", sync);
    window.addEventListener("offline-data-changed", refresh);
    sync();
    return () => {
      window.removeEventListener("online", sync);
      window.removeEventListener("offline-data-changed", refresh);
    };
  }, [refresh, owner]);
  const pack = packs.find((p) => p.key === selected && p.owner_id === owner);
  const activeLesson =
    pack?.lessons.find((l) => l.id === lessonId) || pack?.lessons[0];
  return (
    <main className="offline-reader" lang={language}>
      <header className="sf-surface">
        <span className="sf-eyebrow">SashaInfinity</span>
        <h1>{ta ? "இணையமில்லா கற்றல்" : "Offline learning"}</h1>
        <p>
          {ta
            ? "பாட உரை மற்றும் ஆய்வுகளைப் பதிவிறக்கி ஏழு நாட்கள் பயன்படுத்தலாம்."
            : "Download lesson text and labs for seven days. Work is checked against your enrollment and current content when you reconnect."}
        </p>
        <a className="sf-secondary" href="/courses">
          {ta ? "பாடங்களுக்குத் திரும்பு" : "Back to courses"}
        </a>
      </header>
      {!owner ? (
        <section className="sf-surface">
          <p>
            {ta
              ? "முதலில் இணையத்தில் உள்நுழையவும்."
              : "Sign in online before opening your personal downloads."}
          </p>
          <a href="/login">Sign in</a>
        </section>
      ) : (
        <>
          <section className="sf-surface space-y-3">
            <h2>{ta ? "பதிவிறக்கங்கள்" : "Downloads"}</h2>
            <form
              className="sf-actions"
              onSubmit={async (e) => {
                e.preventDefault();
                setBusy(true);
                setMessage("Downloading course and offline app…");
                try {
                  await downloadCourse(Number(courseId));
                  await refresh();
                  setMessage("Course saved on this device.");
                } catch (error: any) {
                  setMessage(
                    error.response?.data?.detail ||
                      error.message ||
                      "Download failed.",
                  );
                } finally {
                  setBusy(false);
                }
              }}
            >
              <label>
                {ta ? "பாட எண்" : "Course ID"}
                <input
                  type="number"
                  min={1}
                  required
                  value={courseId}
                  onChange={(e) => setCourseId(e.target.value)}
                />
              </label>
              <button className="sf-primary" disabled={busy}>
                {ta ? "பதிவிறக்கு" : "Download enrolled course"}
              </button>
            </form>
            <p className="sf-muted">
              150 MB per course · 250 MB per account. Download requires a
              deployed production build with offline support.
            </p>
            <p role="status">{message}</p>
            {packs
              .filter((p) => p.owner_id === owner)
              .map((p) => (
                <div key={p.key} className="sf-actions">
                  <button
                    className="sf-secondary"
                    onClick={() => setSelected(p.key)}
                  >
                    {p.title} · {(p.bytes / 1048576).toFixed(1)} MB
                  </button>
                  <span>
                    {p.expires < Date.now()
                      ? "Expired"
                      : `Available until ${new Date(p.expires).toLocaleDateString()}`}
                  </span>
                  <button
                    className="sf-secondary"
                    onClick={async () => {
                      await remove("packs", p.key);
                      if (selected === p.key) setSelected(null);
                      await refresh();
                    }}
                  >
                    Remove download
                  </button>
                </div>
              ))}
          </section>
          <section className="sf-surface">
            <h2>
              {ta ? "ஒத்திசைவு" : "Synchronization"} · {events.length}
            </h2>
            <button
              className="sf-secondary"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await syncOffline();
                  await refresh();
                } finally {
                  setBusy(false);
                }
              }}
            >
              {ta ? "இப்போது ஒத்திசை" : "Sync now"}
            </button>
            {events.map((e) => (
              <p key={e.key}>{e.error || "Waiting for connection"}</p>
            ))}
          </section>
          {pack &&
            (pack.expires < Date.now() ? (
              <p role="alert">
                This download expired. Reconnect and download the course again.
              </p>
            ) : activeLesson ? (
              <section className="space-y-4">
                <label className="sf-field">
                  {ta ? "பாடத்தைத் தேர்ந்தெடு" : "Choose a lesson"}
                  <select
                    value={activeLesson.id}
                    onChange={(e) => setLessonId(Number(e.target.value))}
                  >
                    {pack.lessons.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.title}
                      </option>
                    ))}
                  </select>
                </label>
                <Lesson
                  key={`${pack.key}:${activeLesson.id}`}
                  lesson={activeLesson}
                  pack={pack}
                />
              </section>
            ) : (
              <p>This course has no downloadable published lessons.</p>
            ))}
        </>
      )}
      <LearningPreferences />
    </main>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <OfflineReader />
  </React.StrictMode>,
);
