import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { institutionApi, type PlatformPlanRequest } from "@/api/institutions";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { GlassDialog } from "@/components/ui/dialog";
import { apiError } from "./InstitutionDialog";

export function InstitutionPlanQueue() {
  const userId = useAuthStore((s) => s.user?.id);
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: ["institution-plan-queue", userId],
    queryFn: institutionApi.platformRequests,
  });
  const [selected, setSelected] = useState<PlatformPlanRequest | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  return (
    <section className="campus-panel">
      <div className="campus-panel-heading">
        <div>
          <h2>Institution plan requests</h2>
          <p className="campus-muted">
            Platform administration · Review requirements before arranging
            billing.
          </p>
        </div>
        <span className="campus-chip">
          {query.data?.filter((r) => r.status === "pending").length || 0}{" "}
          pending
        </span>
      </div>
      {query.isPending ? (
        <p role="status">Loading requests…</p>
      ) : query.isError ? (
        <p className="campus-error" role="alert">
          Couldn’t load requests.{" "}
          <button onClick={() => void query.refetch()}>Retry</button>
        </p>
      ) : !query.data?.length ? (
        <p className="campus-muted">
          New requests from schools and colleges will appear here.
        </p>
      ) : (
        <div className="campus-table-wrap">
          <table className="campus-table">
            <thead>
              <tr>
                <th>Institution</th>
                <th>Plan</th>
                <th>Requirements</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {query.data.map((r) => (
                <tr key={r.id}>
                  <td>
                    <strong>{r.institution}</strong>
                    <small>{r.contact_email}</small>
                  </td>
                  <td>{r.plan}</td>
                  <td>{r.note || "—"}</td>
                  <td>
                    <span className="campus-chip">{r.status}</span>
                  </td>
                  <td>
                    {r.status === "pending" && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelected(r);
                          setError("");
                        }}
                      >
                        Review<span className="sr-only"> {r.institution}</span>
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {selected && (
        <GlassDialog
          open
          onOpenChange={(open) => {
            if (!open && !pending) setSelected(null);
          }}
          title="Review plan request"
          description={selected.institution}
        >
          <form
            className="campus-form"
            onSubmit={async (e) => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              setPending(true);
              setError("");
              try {
                await institutionApi.reviewRequest(
                  selected.id,
                  String(form.get("status")),
                  String(form.get("note")),
                );
                await cache.invalidateQueries({
                  queryKey: ["institution-plan-queue", userId],
                });
                setSelected(null);
              } catch (err) {
                setError(apiError(err));
              } finally {
                setPending(false);
              }
            }}
          >
            {error && (
              <p className="campus-error" role="alert">
                {error}
              </p>
            )}
            <p className="campus-notice">
              Reviewing this request does not activate a subscription or alter
              limits. Billing and commercial terms are arranged separately.
            </p>
            <label>
              Decision
              <select name="status">
                <option value="reviewed">
                  Reviewed · follow up on requirements
                </option>
                <option value="declined">Declined</option>
              </select>
            </label>
            <label>
              Review note
              <textarea name="note" minLength={3} maxLength={200} required />
            </label>
            <Button type="submit" loading={pending}>
              Save review
            </Button>
          </form>
        </GlassDialog>
      )}
    </section>
  );
}
