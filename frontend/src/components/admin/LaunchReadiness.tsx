import { useEffect, useState } from "react";
import { api } from "@/api/axios";
export function LaunchReadiness() {
  const [data, setData] = useState<any>(null),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    let live = true;
    api
      .get("/admin/operations/readiness")
      .then((r) => {
        if (live) setData(r.data);
      })
      .catch(() => {
        if (live) setMessage("Could not load launch checks.");
      });
    return () => {
      live = false;
    };
  }, []);
  async function probe(provider: string) {
    setBusy(true);
    setMessage("Checking provider connectivity…");
    try {
      setMessage(
        (await api.post(`/admin/operations/readiness/probe/${provider}`)).data
          .detail,
      );
    } catch (e: any) {
      setMessage(e.response?.data?.detail || "Connectivity check failed.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="sf-surface space-y-4">
      <h2>Launch readiness</h2>
      <p>{data?.note || "Checking server setup…"}</p>
      <div className="grid gap-3 md:grid-cols-2">
        {data?.checks.map((c: any) => (
          <article className="rounded-xl border p-4" key={c.key}>
            <h3>{c.label}</h3>
            <strong>{c.status}</strong>
            <p>{c.detail}</p>
          </article>
        ))}
      </div>
      {data?.transcription && (
        <p>
          Local transcription:{" "}
          {data.transcription.configured ? "configured" : "blocked"} ·{" "}
          {data.transcription.note}
        </p>
      )}
      <div className="sf-actions">
        <button
          className="sf-secondary"
          disabled={busy}
          onClick={() => probe("ai")}
        >
          Probe AI connection (small request)
        </button>
        <button
          className="sf-secondary"
          disabled={busy}
          onClick={() => probe("payments")}
        >
          Probe payment connection (read only)
        </button>
      </div>
      <p role="status">{message}</p>
      <p className="sf-muted">
        Before production release, run the documented backup restore rehearsal,
        checkout/webhook test, local load check, and physical AR/VR checks.
        Configuration detection alone does not mark them complete.
      </p>
    </section>
  );
}
