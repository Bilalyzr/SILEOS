/**
 * Cash desk — the day's cash and cheque takings per receiver, with a second
 * owner/admin verifying each entry after counting. Also lists online
 * payments that landed after the balance was already settled (manual refund).
 */
import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Banknote, Download, FileText, ShieldCheck } from "lucide-react";
import toast from "react-hot-toast";
import { campusOsApi, campusOsKeys, useCashDesk, type CashDeskRow } from "@/api/campus-os";
import { openBlob } from "@/api/campus-exams";
import { Button } from "@/components/ui/button";
import { GlassDialog } from "@/components/ui/dialog";
import {
  CampusOsBadge,
  CampusOsEmpty,
  CampusOsError,
  CampusOsLoading,
  errorMessage,
  formatDate,
  formatMoney,
  formatTime,
  readable,
} from "./CampusOsPrimitives";

const localDate = () => {
  const date = new Date();
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 10);
};

export function FeeCashDesk({ institutionId }: { institutionId: number }) {
  const queryClient = useQueryClient();
  const [day, setDay] = useState(localDate);
  const [verifying, setVerifying] = useState<CashDeskRow | null>(null);
  const [note, setNote] = useState("");
  const desk = useCashDesk(institutionId, day);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    try {
      if (new URLSearchParams(window.location.search).get("panel") === "cash") {
        sectionRef.current?.scrollIntoView({ block: "start" });
      }
    } catch {
      /* no window in some test environments */
    }
  }, []);

  const verify = useMutation({
    retry: 0,
    mutationFn: () => {
      if (!verifying) throw new Error("Choose a payment.");
      return campusOsApi.verifyPayment(institutionId, verifying.payment_id, note.trim());
    },
    onSuccess: async () => {
      setVerifying(null);
      setNote("");
      toast.success("Cash verified");
      await queryClient.invalidateQueries({ queryKey: campusOsKeys.fees(institutionId) });
    },
    onError: (cause) => toast.error(errorMessage(cause, "The payment couldn’t be verified.")),
  });

  const exportCsv = useMutation({
    mutationFn: async () => openBlob(await campusOsApi.cashDeskCsv(institutionId, day), `cash-desk-${day}.csv`),
    onError: (cause) => toast.error(errorMessage(cause, "The CSV couldn’t be downloaded.")),
  });

  const receiptPdf = useMutation({
    mutationFn: async (row: CashDeskRow) =>
      openBlob(await campusOsApi.receiptPdf(institutionId, row.receipt_id), `receipt-${row.receipt_number}.pdf`),
    onError: (cause) => toast.error(errorMessage(cause, "The receipt couldn’t be opened.")),
  });

  const currency = desk.data?.currency ?? "INR";

  return (
    <section className="campus-os-panel" id="cash-desk" aria-labelledby="cash-desk-title" ref={sectionRef}>
      <header className="campus-os-panel-head">
        <div>
          <span className="campus-os-section-label">Counter</span>
          <h2 id="cash-desk-title">Cash desk</h2>
          <p>Cash and cheque taken at the counter. A second owner or admin verifies each entry after counting.</p>
        </div>
        <Banknote size={20} color="#a9360c" aria-hidden="true" />
      </header>
      <div className="campus-os-panel-body">
        <div className="campus-os-toolbar">
          <label className="flex items-center gap-2 text-xs font-semibold text-stone-600">
            Day
            <input className="campus-os-control" type="date" value={day} onChange={(event) => setDay(event.target.value)} aria-label="Cash desk day" />
          </label>
          <Button size="sm" variant="outline" leftIcon={<Download size={14} />} loading={exportCsv.isPending} onClick={() => exportCsv.mutate()}>
            Export CSV
          </Button>
        </div>
        {desk.isPending && <CampusOsLoading label="Loading the cash desk" />}
        {desk.isError && <CampusOsError message="The cash desk couldn’t be loaded." retry={() => void desk.refetch()} />}
        {desk.data && (
          <>
            <div className="campus-os-metric-grid">
              <article className="campus-os-metric" data-tone={desk.data.pending_count ? "warning" : "success"}>
                <div className="campus-os-metric-head"><span>Waiting for verification</span><span className="campus-os-metric-icon"><ShieldCheck size={17} /></span></div>
                <strong>{formatMoney(desk.data.pending_total, currency)}</strong>
                <footer>{desk.data.pending_count} {desk.data.pending_count === 1 ? "entry" : "entries"}</footer>
              </article>
              <article className="campus-os-metric" data-tone="success">
                <div className="campus-os-metric-head"><span>Verified</span><span className="campus-os-metric-icon"><Banknote size={17} /></span></div>
                <strong>{formatMoney(desk.data.verified_total, currency)}</strong>
                <footer>Counted by a second person</footer>
              </article>
              <article className="campus-os-metric" data-tone="orange">
                <div className="campus-os-metric-head"><span>Receivers</span><span className="campus-os-metric-icon"><FileText size={17} /></span></div>
                <strong>{desk.data.receivers.length}</strong>
                <footer>{desk.data.receivers.map((r) => `${r.name} ${formatMoney(r.total, currency)}`).join(" · ") || "No cash today"}</footer>
              </article>
            </div>
            {!desk.data.rows.length && <CampusOsEmpty icon={Banknote} title="No cash or cheque on this day" description="Counter payments recorded with a receiver appear here." />}
            {!!desk.data.rows.length && (
              <div className="campus-table-wrap mt-4">
                <table className="campus-table campus-os-table">
                  <caption className="sr-only">Cash desk entries</caption>
                  <thead><tr><th>Student</th><th className="campus-os-hide-mobile">Method</th><th>Amount</th><th className="campus-os-hide-mobile">Received by</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead>
                  <tbody>
                    {desk.data.rows.map((row) => (
                      <tr key={row.payment_id}>
                        <td><strong>{row.student_name}</strong><small>{row.plan_name} · {row.receipt_number}</small></td>
                        <td className="campus-os-hide-mobile">{readable(row.method)}{row.reference ? ` · ${row.reference}` : ""}<small>{formatDate(row.paid_at)} {formatTime(row.paid_at)}</small></td>
                        <td><strong>{formatMoney(row.amount, row.currency)}</strong></td>
                        <td className="campus-os-hide-mobile">{row.received_by?.name ?? "—"}</td>
                        <td>
                          <CampusOsBadge tone={row.verification.status === "verified" ? "success" : row.status !== "posted" ? "neutral" : "warning"}>
                            {row.status !== "posted" ? "Reversed" : row.verification.status === "verified" ? "Verified" : "Pending"}
                          </CampusOsBadge>
                          {row.verification.verified_by && <small className="block">by {row.verification.verified_by.name}</small>}
                        </td>
                        <td>
                          <div className="campus-actions">
                            <Button size="sm" variant="ghost" onClick={() => receiptPdf.mutate(row)}>Receipt PDF</Button>
                            {row.verification.status === "pending" && row.status === "posted" && (
                              <Button size="sm" variant="outline" leftIcon={<ShieldCheck size={14} />} onClick={() => { setNote(""); setVerifying(row); }}>Verify</Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {!!desk.data.excess_orders.length && (
              <div className="mt-5">
                <span className="campus-os-section-label">Online payments needing a refund</span>
                <ul className="campus-activity">
                  {desk.data.excess_orders.map((order) => (
                    <li key={order.id}>
                      <strong>{order.student_name}</strong> · {formatMoney(order.excess_amount, order.currency)} arrived online after the balance was settled at the counter.{" "}
                      <span className="campus-muted">Refund manually in the Razorpay dashboard ({order.gateway_payment_id}).</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>

      <GlassDialog open={Boolean(verifying)} onOpenChange={(open) => { if (!open) setVerifying(null); }} title={verifying ? `Verify cash · ${verifying.student_name}` : "Verify cash"} eyebrow="Cash desk" description="Confirm you counted this money. The receiver cannot verify their own entry." size="md">
        <form className="campus-form" onSubmit={(event) => { event.preventDefault(); verify.mutate(); }}>
          {verifying && (
            <p className="campus-notice">
              {formatMoney(verifying.amount, verifying.currency)} · {readable(verifying.method)} · received by {verifying.received_by?.name ?? "—"}
            </p>
          )}
          <label>Note<textarea name="note" maxLength={300} rows={3} value={note} onChange={(event) => setNote(event.target.value)} placeholder="Counted and matched the drawer" /></label>
          <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={() => setVerifying(null)}>Cancel</Button><Button type="submit" loading={verify.isPending}>Mark verified</Button></div>
        </form>
      </GlassDialog>
    </section>
  );
}

export default FeeCashDesk;
