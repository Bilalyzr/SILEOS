import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/axios";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { GlassDialog } from "@/components/ui/dialog";
import { apiError } from "./InstitutionDialog";
type Attempt = {
  id: number;
  institution_id: number;
  plan: string;
  status: string;
  subscription_id: string | null;
};
export function BillingRecovery() {
  const uid = useAuthStore((s) => s.user?.id);
  const [selected, setSelected] = useState<Attempt>();
  const [sub, setSub] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const q = useQuery({
    queryKey: ["campus-billing-recovery", uid],
    queryFn: async () =>
      (await api.get<Attempt[]>("/institutions/platform/billing-attempts"))
        .data,
  });
  return (
    <section className="campus-panel">
      <h2>Subscription recovery</h2>
      <p className="campus-muted my-4">
        Match interrupted checkout attempts to the provider’s subscription.
        Identity is verified against the saved campus and plan before any
        update.
      </p>
      {q.isError && (
        <Button onClick={() => q.refetch()}>Retry subscription list</Button>
      )}
      {q.data?.length === 0 && (
        <p className="campus-muted">No institution checkout attempts yet.</p>
      )}
      {q.data?.map((r) => (
        <div className="campus-step" key={r.id}>
          <div className="campus-step-copy">
            <strong>
              Campus {r.institution_id} · {r.plan}
            </strong>
            <p>
              Attempt {r.id} · {r.status}
            </p>
          </div>
          <Button
            variant="outline"
            onClick={() => {
              setSelected(r);
              setSub(r.subscription_id || "");
              setError("");
            }}
          >
            Reconcile
          </Button>
        </div>
      ))}
      <GlassDialog
        open={!!selected}
        onOpenChange={(v) => {
          if (!v) setSelected(undefined);
        }}
        title="Reconcile provider subscription"
      >
        <form
          className="campus-form"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError("");
            try {
              await api.post(
                `/institutions/platform/billing-attempts/${selected!.id}/reconcile`,
                { subscription_id: sub },
              );
              await q.refetch();
              setSelected(undefined);
            } catch (err) {
              setError(apiError(err));
            } finally {
              setBusy(false);
            }
          }}
        >
          <p>
            Use the subscription ID from the Razorpay dashboard. This will not
            create a new subscription or charge a customer.
          </p>
          <label>
            Razorpay subscription ID
            <input
              required
              pattern="sub_[A-Za-z0-9]+"
              value={sub}
              onChange={(e) => setSub(e.target.value)}
            />
          </label>
          {error && (
            <p role="alert" className="campus-error">
              {error}
            </p>
          )}
          <Button type="submit" disabled={busy}>
            Verify and reconcile
          </Button>
        </form>
      </GlassDialog>
    </section>
  );
}
