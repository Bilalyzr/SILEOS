import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/axios";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { apiError } from "./InstitutionDialog";
export function GuardianRequests() {
  const user = useAuthStore((s) => s.user);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const q = useQuery({
    queryKey: ["guardian-requests", user?.id],
    queryFn: async () =>
      (
        await api.get<
          {
            id: number;
            parent_name: string;
            parent_email: string;
            status: string;
          }[]
        >("/parents/access-requests")
      ).data,
    enabled: user?.role === "student",
  });
  if (!q.data?.length) return null;
  return (
    <section className="campus-panel my-6">
      <h2>Guardian access requests</h2>
      <p className="campus-muted my-3">
        Approve someone you know to see your learning summaries. You can revoke
        their access here at any time.
      </p>
      {error && (
        <p className="campus-error" role="alert">
          {error}
        </p>
      )}
      {q.data.map((r) => (
        <div className="campus-step" key={r.id}>
          <div className="campus-step-copy">
            <strong>{r.parent_name}</strong>
            <p>
              {r.parent_email} · {r.status}
            </p>
          </div>
          <div className="campus-actions">
            {(r.status === "approved"
              ? ["revoked"]
              : ["approved", "declined"]
            ).map((status) => (
              <Button
                variant={status === "approved" ? "default" : "outline"}
                key={status}
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  setError("");
                  try {
                    await api.patch(`/parents/access-requests/${r.id}`, {
                      status,
                    });
                    await q.refetch();
                  } catch (e) {
                    setError(apiError(e));
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {status === "approved"
                  ? "Approve"
                  : status === "declined"
                    ? "Decline"
                    : "Revoke access"}
              </Button>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
