import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { campusApi, type CampusPrice } from "@/api/campus";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { GlassDialog } from "@/components/ui/dialog";
import { apiError } from "./InstitutionDialog";

export function CampusBilling({ id, owner }: { id: number; owner: boolean }) {
  const user = useAuthStore((s) => s.user);
  const q = useQuery({
    queryKey: ["campus-billing", user?.id, id],
    queryFn: () => campusApi.billing(id),
  });
  const [price, setPrice] = useState<CampusPrice>();
  const [cancel, setCancel] = useState<number>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [invoices, setInvoices] =
    useState<Awaited<ReturnType<typeof campusApi.invoices>>>();
  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await q.refetch();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="campus-panel">
      <div className="campus-toolbar">
        <h2>Subscription & invoices</h2>
        <Button variant="ghost" onClick={() => q.refetch()}>
          Refresh status
        </Button>
      </div>
      <p className="campus-muted my-4">
        Paid capacity follows confirmed billing periods. Cancellation keeps your
        paid access until the end of the period.
      </p>
      {q.isError && (
        <p role="alert" className="campus-error">
          Billing could not be loaded. Refresh to retry.
        </p>
      )}
      {error && (
        <p role="alert" className="campus-error">
          {error}
        </p>
      )}
      {q.data?.plans.length === 0 && (
        <p className="campus-notice">
          Online institutional checkout is not configured yet. You can submit a
          plan request below.
        </p>
      )}
      <div className="campus-actions">
        {q.data?.plans.map((p) => (
          <Button
            disabled={!owner || busy}
            key={p}
            onClick={() =>
              run(async () => setPrice(await campusApi.price(id, p)))
            }
          >
            View {p} price
          </Button>
        ))}
      </div>
      {q.data?.subscriptions.map((s) => (
        <div className="campus-step" key={s.id}>
          <div className="campus-step-copy">
            <strong>{s.plan}</strong>
            <p>
              {s.status.replace(/_/g, " ")}
              {s.paid_through &&
                ` · Paid through ${new Date(s.paid_through).toLocaleDateString()}`}
            </p>
            {s.status === "creating" && (
              <p>
                Checkout requires administrator reconciliation before another
                attempt.
              </p>
            )}
          </div>
          <div className="campus-actions">
            {s.checkout_url && s.status === "created" && owner && (
              <a
                className="sf-primary"
                href={s.checkout_url}
                target="_blank"
                rel="noreferrer"
              >
                Continue checkout
              </a>
            )}
            <Button
              variant="outline"
              disabled={busy}
              onClick={() =>
                run(async () => setInvoices(await campusApi.invoices(id, s.id)))
              }
            >
              Invoices
            </Button>
            {owner &&
              ![
                "cancelled",
                "completed",
                "expired",
                "cancel_scheduled",
                "creating",
              ].includes(s.status) && (
                <Button variant="ghost" onClick={() => setCancel(s.id)}>
                  Cancel renewal
                </Button>
              )}
          </div>
        </div>
      ))}
      <GlassDialog
        open={!!price}
        onOpenChange={(v) => {
          if (!v) setPrice(undefined);
        }}
        title="Review your subscription"
      >
        <p className="campus-notice">
          {price &&
            `${price.name}: ${new Intl.NumberFormat(undefined, { style: "currency", currency: price.currency || "INR" }).format(price.amount / 100)} every ${price.interval} ${price.period} period(s), for ${price.total_cycles} cycles.`}
        </p>
        <p className="brand-share-note my-4">
          Razorpay will show the final payment terms and request your
          authorization. No capacity changes until a paid cycle is confirmed.
        </p>
        {error && (
          <p role="alert" className="campus-error">
            {error}
          </p>
        )}
        <Button
          disabled={busy}
          onClick={() =>
            run(async () => {
              const result = await campusApi.subscribe(
                id,
                price!.plan,
                price!.gateway_plan_id,
              );
              setPrice(undefined);
              if (result.checkout_url)
                window.location.assign(result.checkout_url);
              else
                throw new Error(
                  "Checkout URL unavailable. Refresh the subscription status.",
                );
            })
          }
        >
          Continue to secure checkout
        </Button>
      </GlassDialog>
      <GlassDialog
        open={!!cancel}
        onOpenChange={(v) => {
          if (!v) setCancel(undefined);
        }}
        title="Cancel automatic renewal?"
      >
        <p>
          Your paid capacity remains available until the end of the current
          billing period. Your campus data is retained.
        </p>
        {error && (
          <p role="alert" className="campus-error">
            {error}
          </p>
        )}
        <Button
          className="mt-4"
          disabled={busy}
          onClick={() =>
            run(async () => {
              await campusApi.cancel(id, cancel!);
              setCancel(undefined);
            })
          }
        >
          Cancel at period end
        </Button>
      </GlassDialog>
      <GlassDialog
        open={!!invoices}
        onOpenChange={(v) => {
          if (!v) setInvoices(undefined);
        }}
        title="Institution invoices"
      >
        {invoices?.length === 0 && (
          <p>No invoices have been issued for this subscription.</p>
        )}
        {invoices?.map((i) => (
          <div className="campus-step" key={i.id}>
            <div className="campus-step-copy">
              <strong>{i.id}</strong>
              <p>
                {i.status} · {i.currency} {(i.amount / 100).toFixed(2)}
              </p>
            </div>
            {i.url && (
              <a
                href={i.url}
                target="_blank"
                rel="noreferrer"
                className="brand-text-link"
              >
                Open invoice →
              </a>
            )}
          </div>
        ))}
      </GlassDialog>
    </section>
  );
}
