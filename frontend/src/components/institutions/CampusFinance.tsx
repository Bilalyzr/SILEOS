import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  BadgeIndianRupee,
  Banknote,
  CalendarClock,
  CheckCircle2,
  CreditCard,
  FilePlus2,
  FileText,
  GraduationCap,
  Plus,
  Receipt,
  ShieldCheck,
  Sparkles,
  Trash2,
  UserCheck,
  WalletCards,
} from "lucide-react";
import toast from "react-hot-toast";
import type { InstitutionOverview } from "@/api/institutions";
import {
  campusOsApi,
  campusOsKeys,
  type CampusOsRole,
  type FeeAgingRow,
  type FeeComponent,
  type FeeInstallment,
  type TuitionAssignment,
  type TuitionPayment,
  useFeeAging,
  useFeePlans,
  useFeeSelf,
  useFeeSummary,
  useOnlineStatus,
} from "@/api/campus-os";
import { openBlob } from "@/api/campus-exams";
import { openRazorpay } from "@/lib/razorpayCheckout";
import { useAuthStore } from "@/store/auth";
import { PageBanner } from "@/components/design-system/PageBanner";
import { FeeCashDesk } from "./FeeCashDesk";
import { FeeReminders, REASONS } from "./FeeReminders";
import { remindersApi } from "@/api/tuition-reminders";
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
  initials,
  readable,
} from "./CampusOsPrimitives";
import "@/styles/campus-os.css";

export interface CampusFinanceProps {
  data: InstitutionOverview;
  role?: CampusOsRole;
  studentUserId?: number;
  demo?: boolean;
}

type DraftComponent = Omit<FeeComponent, "id" | "amount"> & { amount: string };
type DraftInstallment = Omit<FeeInstallment, "id" | "sequence" | "amount"> & { amount: string };

const emptyComponent = (): DraftComponent => ({ code: "", name: "", amount: "" });
const emptyInstallment = (): DraftInstallment => ({ name: "", due_on: "", amount: "" });
const localDate = () => {
  const date = new Date();
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 10);
};
const localDateTime = () => {
  const date = new Date();
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
};
const idempotencyKey = (prefix: string) =>
  `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

function ManagerFinance({ data, demo }: { data: InstitutionOverview; demo: boolean }) {
  const queryClient = useQueryClient();
  const [asOf, setAsOf] = useState(localDate);
  const [planOpen, setPlanOpen] = useState(false);
  const [assignmentOpen, setAssignmentOpen] = useState(false);
  const [paymentFor, setPaymentFor] = useState<FeeAgingRow | null>(null);
  const [method, setMethod] = useState("upi");
  const [formError, setFormError] = useState("");
  const [components, setComponents] = useState<DraftComponent[]>([emptyComponent()]);
  const [installments, setInstallments] = useState<DraftInstallment[]>([emptyInstallment()]);
  const currentUserId = useAuthStore((state) => state.user?.id);

  const summary = useFeeSummary(data.institution.id, asOf, demo);
  const aging = useFeeAging(data.institution.id, asOf, demo);
  const plans = useFeePlans(data.institution.id, demo);
  const students = data.members.filter((member) => member.role === "student" && member.status === "active");
  const receivers = data.members.filter((member) => ["owner", "admin", "teacher"].includes(member.role) && member.status === "active");
  const myMemberId = receivers.find((member) => member.user_id === currentUserId)?.id;
  const cashMethod = method === "cash" || method === "cheque";
  const currency = summary.data?.currency || "INR";
  const mixedCurrency = summary.data?.mixed_currency ?? false;
  const money = (amount: number) => mixedCurrency ? "Mixed" : formatMoney(amount, currency);

  const planTotal = useMemo(
    () => components.reduce((sum, row) => sum + (Number(row.amount) || 0), 0),
    [components],
  );
  const installmentTotal = useMemo(
    () => installments.reduce((sum, row) => sum + (Number(row.amount) || 0), 0),
    [installments],
  );

  async function refreshFees() {
    await queryClient.invalidateQueries({ queryKey: campusOsKeys.fees(data.institution.id) });
  }

  const createPlan = useMutation({
    mutationFn: async (form: HTMLFormElement) => {
      const fields = new FormData(form);
      if (Math.abs(planTotal - installmentTotal) > 0.001) {
        throw new Error("Fee component and installment totals must match exactly.");
      }
      if (components.some((row) => !row.code.trim() || !row.name.trim() || Number(row.amount) <= 0)) {
        throw new Error("Complete every fee component with a code, name and positive amount.");
      }
      if (installments.some((row) => !row.name.trim() || !row.due_on || Number(row.amount) <= 0)) {
        throw new Error("Complete every installment with a name, due date and positive amount.");
      }
      if (demo) return null;
      return campusOsApi.createFeePlan(data.institution.id, {
        name: String(fields.get("name") || "").trim(),
        academic_year: String(fields.get("academic_year") || "").trim(),
        currency: String(fields.get("currency") || "INR").trim().toUpperCase(),
        description: String(fields.get("description") || "").trim(),
        components: components.map((row) => ({ ...row, code: row.code.trim().toUpperCase(), name: row.name.trim(), amount: Number(row.amount) })),
        installments: installments.map((row) => ({ ...row, name: row.name.trim(), amount: Number(row.amount) })),
      });
    },
    onSuccess: async () => {
      if (!demo) await refreshFees();
      setPlanOpen(false);
      setComponents([emptyComponent()]);
      setInstallments([emptyInstallment()]);
      setFormError("");
      toast.success(demo ? "Fee plan form checked" : "Fee plan saved as draft");
    },
    onError: (cause) => setFormError(errorMessage(cause, "The fee plan couldn’t be saved.")),
  });

  const assignPlan = useMutation({
    mutationFn: async (form: HTMLFormElement) => {
      const fields = new FormData(form);
      if (demo) return null;
      return campusOsApi.createFeeAssignment(data.institution.id, {
        student_member_id: Number(fields.get("student_member_id")),
        plan_id: Number(fields.get("plan_id")),
        note: String(fields.get("note") || "").trim(),
      });
    },
    onSuccess: async () => {
      if (!demo) await refreshFees();
      setAssignmentOpen(false);
      setFormError("");
      toast.success(demo ? "Assignment form checked" : "Fee plan assigned");
    },
    onError: (cause) => setFormError(errorMessage(cause, "The fee plan couldn’t be assigned.")),
  });

  const recordPayment = useMutation({
    mutationFn: async (form: HTMLFormElement) => {
      if (!paymentFor) throw new Error("Choose a student account.");
      const fields = new FormData(form);
      if (demo) return null;
      return campusOsApi.recordFeePayment(
        data.institution.id,
        paymentFor.assignment_id,
        {
          amount: Number(fields.get("amount")),
          paid_at: String(fields.get("paid_at") || "") ? new Date(String(fields.get("paid_at"))).toISOString() : null,
          method: String(fields.get("method")),
          reference: String(fields.get("reference") || "").trim(),
          note: String(fields.get("note") || "").trim(),
          received_by_member_id: fields.get("received_by_member_id") ? Number(fields.get("received_by_member_id")) : null,
        },
        idempotencyKey(`fee-${paymentFor.assignment_id}`),
      );
    },
    onSuccess: async () => {
      if (!demo) await refreshFees();
      setPaymentFor(null);
      setFormError("");
      toast.success(demo ? "Payment form checked" : "Payment recorded and receipt issued");
    },
    onError: (cause) => setFormError(errorMessage(cause, "The payment couldn’t be recorded.")),
  });

  const invoice = useMutation({
    retry: 0,
    mutationFn: async (row: FeeAgingRow) => {
      const created = await campusOsApi.createInvoice(data.institution.id, row.assignment_id, null);
      openBlob(await campusOsApi.invoicePdf(data.institution.id, created.id), `invoice-${created.invoice_number}.pdf`);
      return created;
    },
    onSuccess: (created) => toast.success(`Invoice ${created.invoice_number} issued`),
    onError: (cause) => toast.error(errorMessage(cause, "The invoice couldn’t be issued.")),
  });

  const publishPlan = useMutation({
    mutationFn: async (planId: number) => {
      if (!demo) await campusOsApi.publishFeePlan(data.institution.id, planId);
      return planId;
    },
    onSuccess: async () => {
      if (!demo) await refreshFees();
      toast.success(demo ? "Publish action previewed" : "Fee plan published");
    },
    onError: (cause) => toast.error(errorMessage(cause, "The fee plan couldn’t be published.")),
  });

  const remind = useMutation({
    mutationFn: (assignmentId: number) => remindersApi.remind(data.institution.id, assignmentId),
    onSuccess: (rows) => {
      const sent = rows.filter((row) => row.status === "sent").length;
      toast[sent ? "success" : "error"](sent ? `Reminder sent to ${sent} recipient${sent === 1 ? "" : "s"}` : rows[0]?.error || (rows[0]?.skip_reason ? REASONS[rows[0].skip_reason] ?? rows[0].skip_reason : "No reminder could be sent."));
      void queryClient.invalidateQueries({ queryKey: ["fee-reminders", data.institution.id] });
    },
    onError: (cause) => toast.error(errorMessage(cause, "The reminder couldn’t be sent.")),
  });

  return (
    <>
      <div className="campus-os-banner">
        <PageBanner
          eyebrow="Student finance · Clear and accountable"
          title="Make every fee, payment and receipt easy to understand."
          description="Plan tuition, track dues and support families with one reliable student ledger."
          share
          shareTitle={`${data.institution.name} · Student finance`}
          shareDescription="A clear, secure student fee experience powered by SashaInfinity."
          actions={
            <>
              <Button variant="outline" leftIcon={<UserCheck size={16} />} onClick={() => setAssignmentOpen(true)}>Assign fee plan</Button>
              <Button leftIcon={<FilePlus2 size={16} />} onClick={() => setPlanOpen(true)}>New fee plan</Button>
            </>
          }
        />
      </div>

      <div className="campus-os-toolbar">
        <div>
          <span className="campus-os-section-label">Ledger position</span>
          <p className="mt-1 text-xs text-stone-600">Balances are calculated from immutable assessments, adjustments and payments.</p>
        </div>
        <label className="flex items-center gap-2 text-xs font-semibold text-stone-600">
          As of
          <input className="campus-os-control" type="date" value={asOf} onChange={(event) => setAsOf(event.target.value)} />
        </label>
      </div>

      {summary.isPending && <CampusOsLoading label="Loading student finance overview" />}
      {summary.isError && <CampusOsError message="The fee summary couldn’t be loaded." retry={() => void summary.refetch()} />}
      {summary.data && (
        <>
          {summary.data.mixed_currency && <p className="campus-notice" role="status">This institution has accounts in more than one currency. Totals are labelled as mixed; account rows retain their own currency.</p>}
          <div className="campus-os-metric-grid" aria-label="Student finance key numbers">
            {[
              { label: "Assessed", value: money(summary.data.totals.assessed), detail: `${summary.data.accounts.total} student accounts`, icon: Receipt, tone: "orange" },
              { label: "Collected", value: money(summary.data.totals.paid), detail: "Posted payments", icon: CheckCircle2, tone: "success" },
              { label: "Outstanding", value: money(summary.data.totals.outstanding), detail: `${summary.data.accounts.with_balance} accounts`, icon: WalletCards, tone: "warning" },
              { label: "Overdue", value: money(summary.data.totals.overdue), detail: `${summary.data.accounts.overdue} accounts need follow-up`, icon: CalendarClock, tone: summary.data.totals.overdue > 0 ? "danger" : "success" },
            ].map((item) => (
              <article className="campus-os-metric" data-tone={item.tone} key={item.label}>
                <div className="campus-os-metric-head"><span>{item.label}</span><span className="campus-os-metric-icon"><item.icon size={17} /></span></div>
                <strong>{item.value}</strong>
                <footer>{item.detail}</footer>
              </article>
            ))}
          </div>

          <section className="campus-os-panel" aria-labelledby="aging-title">
            <header className="campus-os-panel-head">
              <div><span className="campus-os-section-label">Receivables</span><h2 id="aging-title">Outstanding by age</h2><p>Older balances rise to the front of the follow-up queue.</p></div>
              <BadgeIndianRupee size={20} color="#a9360c" aria-hidden="true" />
            </header>
            <div className="campus-os-panel-body pt-4">
              <div className="campus-os-aging-grid">
                {[
                  ["Current", summary.data.aging.current, false],
                  ["1–30 days", summary.data.aging.days_1_30, false],
                  ["31–60 days", summary.data.aging.days_31_60, false],
                  ["61–90 days", summary.data.aging.days_61_90, true],
                  ["91+ days", summary.data.aging.days_91_plus, true],
                ].map(([label, value, risk]) => (
                  <article className="campus-os-aging-card" data-risk={risk ? "high" : undefined} key={String(label)}><span>{label}</span><strong>{money(Number(value))}</strong></article>
                ))}
              </div>
            </div>
          </section>
        </>
      )}

      <div className="campus-os-columns">
        <section className="campus-os-panel" aria-labelledby="fee-accounts-title">
          <header className="campus-os-panel-head">
            <div><span className="campus-os-section-label">Family follow-up</span><h2 id="fee-accounts-title">Accounts needing attention</h2><p>Record a received payment from the exact student ledger.</p></div>
            <ShieldCheck size={20} color="#a9360c" aria-hidden="true" />
          </header>
          <div className="campus-os-panel-body">
            {aging.isPending && <CampusOsLoading label="Loading outstanding student accounts" />}
            {aging.isError && <CampusOsError message="Outstanding accounts couldn’t be loaded." retry={() => void aging.refetch()} />}
            {aging.data && !aging.data.rows.length && <CampusOsEmpty icon={CheckCircle2} title="No overdue balances" description="Accounts with a balance due will appear here with the oldest due date first." />}
            {!!aging.data?.rows.length && (
              <div className="campus-table-wrap">
                <table className="campus-table campus-os-table">
                  <caption className="sr-only">Student fee accounts needing attention</caption>
                  <thead><tr><th>Student</th><th className="campus-os-hide-mobile">Oldest due</th><th>Balance</th><th><span className="sr-only">Actions</span></th></tr></thead>
                  <tbody>
                    {aging.data.rows.map((row) => (
                      <tr key={row.assignment_id}>
                        <td><div className="campus-os-person"><span className="campus-os-avatar">{initials(row.student_name)}</span><span><strong>{row.student_name}</strong><small>{row.plan_name}</small></span></div></td>
                        <td className="campus-os-hide-mobile">{formatDate(row.oldest_due_on)}<small>{formatMoney(row.overdue, row.currency)} overdue</small></td>
                        <td><strong>{formatMoney(row.outstanding, row.currency)}</strong></td>
                        <td><div className="campus-actions"><Button size="sm" variant="outline" leftIcon={<Banknote size={14} />} onClick={() => { setFormError(""); setMethod("upi"); setPaymentFor(row); }}>Record payment</Button><Button size="sm" variant="ghost" leftIcon={<FileText size={14} />} loading={invoice.isPending && invoice.variables?.assignment_id === row.assignment_id} onClick={() => invoice.mutate(row)}>Invoice</Button><Button size="sm" variant="ghost" loading={remind.isPending && remind.variables === row.assignment_id} onClick={() => remind.mutate(row.assignment_id)}>Send reminder</Button></div></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

        <aside className="campus-os-panel" aria-labelledby="fee-plans-title">
          <header className="campus-os-panel-head">
            <div><span className="campus-os-section-label">Fee structures</span><h2 id="fee-plans-title">Plans</h2><p>Publish only when components and installments match.</p></div>
          </header>
          <div className="campus-os-panel-body pt-4">
            {plans.isPending && <CampusOsLoading label="Loading fee plans" />}
            {plans.isError && <CampusOsError message="Fee plans couldn’t be loaded." retry={() => void plans.refetch()} />}
            {plans.data && !plans.data.items.length && <CampusOsEmpty icon={Receipt} title="Create your first fee plan" description="Define fee components and matching installments for an academic year." action={<Button size="sm" leftIcon={<Plus size={14} />} onClick={() => setPlanOpen(true)}>New fee plan</Button>} />}
            <div className="campus-os-plan-list">
              {plans.data?.items.map((plan) => (
                <article className="campus-os-plan-card" key={plan.id}>
                  <div className="campus-os-row-between"><h3>{plan.name}</h3><CampusOsBadge tone={plan.status === "published" ? "success" : "neutral"}>{plan.status}</CampusOsBadge></div>
                  <p>{plan.academic_year} · {plan.components.length} components · {plan.installments.length} installments</p>
                  <div className="campus-os-row-between"><strong>{formatMoney(plan.total_amount, plan.currency)}</strong>{plan.status === "draft" && <Button size="sm" variant="outline" loading={publishPlan.isPending} onClick={() => publishPlan.mutate(plan.id)}>Publish</Button>}</div>
                </article>
              ))}
            </div>
          </div>
        </aside>
      </div>

      {!demo && <FeeCashDesk institutionId={data.institution.id} />}
      {!demo && <FeeReminders institutionId={data.institution.id} />}

      <GlassDialog open={planOpen} onOpenChange={(open) => { setPlanOpen(open); if (!open) setFormError(""); }} title="Create a fee plan" eyebrow="Student finance" description="Component and installment totals must match exactly before the plan can be published." size="lg">
        <form className="campus-form" onSubmit={(event) => { event.preventDefault(); setFormError(""); createPlan.mutate(event.currentTarget); }}>
          {demo && <p className="campus-notice"><Sparkles size={14} className="mr-2 inline" />Preview mode validates this plan without saving it.</p>}
          {formError && <p className="campus-error" role="alert">{formError}</p>}
          <div className="campus-form-grid"><label>Plan name<input name="name" required maxLength={160} placeholder="Grade 11 · 2026–27" /></label><label>Academic year<input name="academic_year" required maxLength={32} defaultValue={data.institution.academic_year} /></label></div>
          <div className="campus-form-grid"><label>Currency<input name="currency" required pattern="[A-Za-z]{3}" maxLength={3} defaultValue="INR" /></label><label>Description<input name="description" maxLength={1000} placeholder="Annual tuition and campus services" /></label></div>
          <fieldset className="campus-panel p-4"><legend className="px-2 text-sm font-bold text-stone-800">Fee components</legend><div className="space-y-3">{components.map((row, index) => <div className="grid gap-2 sm:grid-cols-[0.8fr_1.4fr_1fr_auto]" key={index}><label>Code<input aria-label={`Component ${index + 1} code`} value={row.code} maxLength={40} onChange={(event) => setComponents((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, code: event.target.value } : item))} /></label><label>Name<input aria-label={`Component ${index + 1} name`} value={row.name} maxLength={120} onChange={(event) => setComponents((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, name: event.target.value } : item))} /></label><label>Amount<input aria-label={`Component ${index + 1} amount`} type="number" min="0.01" step="0.01" value={row.amount} onChange={(event) => setComponents((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, amount: event.target.value } : item))} /></label><button className="campus-os-icon-button self-end" type="button" aria-label={`Remove component ${index + 1}`} disabled={components.length === 1} onClick={() => setComponents((items) => items.filter((_, itemIndex) => itemIndex !== index))}><Trash2 size={14} /></button></div>)}</div><Button className="mt-3" type="button" size="sm" variant="outline" leftIcon={<Plus size={14} />} onClick={() => setComponents((items) => [...items, emptyComponent()])}>Add component</Button></fieldset>
          <fieldset className="campus-panel p-4"><legend className="px-2 text-sm font-bold text-stone-800">Installments</legend><div className="space-y-3">{installments.map((row, index) => <div className="grid gap-2 sm:grid-cols-[1.3fr_1fr_1fr_auto]" key={index}><label>Name<input aria-label={`Installment ${index + 1} name`} value={row.name} maxLength={120} onChange={(event) => setInstallments((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, name: event.target.value } : item))} /></label><label>Due date<input aria-label={`Installment ${index + 1} due date`} type="date" value={row.due_on} onChange={(event) => setInstallments((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, due_on: event.target.value } : item))} /></label><label>Amount<input aria-label={`Installment ${index + 1} amount`} type="number" min="0.01" step="0.01" value={row.amount} onChange={(event) => setInstallments((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, amount: event.target.value } : item))} /></label><button className="campus-os-icon-button self-end" type="button" aria-label={`Remove installment ${index + 1}`} disabled={installments.length === 1} onClick={() => setInstallments((items) => items.filter((_, itemIndex) => itemIndex !== index))}><Trash2 size={14} /></button></div>)}</div><Button className="mt-3" type="button" size="sm" variant="outline" leftIcon={<Plus size={14} />} onClick={() => setInstallments((items) => [...items, emptyInstallment()])}>Add installment</Button></fieldset>
          <div className="campus-os-row-between rounded-xl bg-orange-50 p-3 text-sm"><span>Components: <strong>{formatMoney(planTotal)}</strong></span><span>Installments: <strong>{formatMoney(installmentTotal)}</strong></span></div>
          <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={() => setPlanOpen(false)}>Cancel</Button><Button type="submit" loading={createPlan.isPending}>Save draft plan</Button></div>
        </form>
      </GlassDialog>

      <GlassDialog open={assignmentOpen} onOpenChange={(open) => { setAssignmentOpen(open); if (!open) setFormError(""); }} title="Assign a fee plan" eyebrow="Student ledger" description="A student can receive each fee plan once. The assignment creates their auditable ledger." size="md">
        <form className="campus-form" onSubmit={(event) => { event.preventDefault(); setFormError(""); assignPlan.mutate(event.currentTarget); }}>
          {formError && <p className="campus-error" role="alert">{formError}</p>}
          <label>Student<select name="student_member_id" required defaultValue=""><option value="" disabled>Choose a student</option>{students.map((student) => <option key={student.id} value={student.id}>{student.name} · {student.email}</option>)}</select></label>
          <label>Published fee plan<select name="plan_id" required defaultValue=""><option value="" disabled>Choose a plan</option>{plans.data?.items.filter((plan) => plan.status === "published").map((plan) => <option key={plan.id} value={plan.id}>{plan.name} · {formatMoney(plan.total_amount, plan.currency)}</option>)}</select></label>
          <label>Internal note<textarea name="note" maxLength={500} rows={3} /></label>
          {!students.length && <p className="campus-notice">Add an active student member before assigning a fee plan.</p>}
          {!plans.data?.items.some((plan) => plan.status === "published") && <p className="campus-notice">Publish a fee plan before assigning it.</p>}
          <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={() => setAssignmentOpen(false)}>Cancel</Button><Button type="submit" loading={assignPlan.isPending} disabled={!students.length || !plans.data?.items.some((plan) => plan.status === "published")}>Assign plan</Button></div>
        </form>
      </GlassDialog>

      <GlassDialog open={Boolean(paymentFor)} onOpenChange={(open) => { if (!open) { setPaymentFor(null); setFormError(""); } }} title={paymentFor ? `Record payment · ${paymentFor.student_name}` : "Record payment"} eyebrow="Student ledger" description="Submitting once creates a posted payment and numbered receipt. The idempotency key protects against duplicate clicks." size="md">
        <form className="campus-form" onSubmit={(event) => { event.preventDefault(); setFormError(""); recordPayment.mutate(event.currentTarget); }}>
          {formError && <p className="campus-error" role="alert">{formError}</p>}
          {paymentFor && <p className="campus-notice">Outstanding balance: <strong>{formatMoney(paymentFor.outstanding, paymentFor.currency)}</strong></p>}
          <div className="campus-form-grid"><label>Amount<input name="amount" type="number" required min="0.01" step="0.01" max={paymentFor?.outstanding} /></label><label>Paid at<input name="paid_at" type="datetime-local" defaultValue={localDateTime()} /></label></div>
          <div className="campus-form-grid"><label>Method<select name="method" required value={method} onChange={(event) => setMethod(event.target.value)}><option value="upi">UPI</option><option value="bank_transfer">Bank transfer</option><option value="cash">Cash</option><option value="card">Card</option><option value="cheque">Cheque</option><option value="online">Online gateway</option></select></label><label>Reference<input name="reference" maxLength={120} placeholder="Transaction or receipt reference" /></label></div>
          {cashMethod && (
            <label>Received by<select name="received_by_member_id" required defaultValue={myMemberId ?? ""}><option value="" disabled>Choose the staff member who took it</option>{receivers.map((member) => <option key={member.id} value={member.id}>{member.name} · {readable(member.role)}</option>)}</select></label>
          )}
          {cashMethod && <p className="campus-notice">Cash and cheque stay “pending” until another owner or admin verifies the count on the cash desk.</p>}
          <label>Note<textarea name="note" maxLength={500} rows={3} /></label>
          <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={() => setPaymentFor(null)}>Cancel</Button><Button type="submit" loading={recordPayment.isPending}>Record and issue receipt</Button></div>
        </form>
      </GlassDialog>
    </>
  );
}

function LearnerFinance({
  data,
  studentUserId,
  demo,
}: {
  data: InstitutionOverview;
  studentUserId?: number;
  demo: boolean;
}) {
  const accounts = useFeeSelf(data.institution.id, studentUserId, demo);
  const online = useOnlineStatus(data.institution.id, !demo);
  const assignments = accounts.data?.assignments ?? [];
  const totalBalance = assignments.reduce((sum, item) => sum + item.balance, 0);
  const totalPaid = assignments.reduce((sum, item) => sum + item.paid_total, 0);
  const nextInstallment = assignments
    .flatMap((assignment) => assignment.installments.map((installment) => ({ ...installment, currency: assignment.currency })))
    .filter((installment) => installment.balance > 0)
    .sort((a, b) => a.due_on.localeCompare(b.due_on))[0];
  const onlineReady = online.data?.ready ?? false;

  const payOnline = useMutation({
    retry: 0,
    mutationFn: async ({ assignment, installmentId }: { assignment: TuitionAssignment; installmentId: number | null }) => {
      const { order, checkout } = await campusOsApi.createOnlineOrder(data.institution.id, assignment.id, { installment_id: installmentId, amount: null });
      await openRazorpay(checkout, {
        onSuccess: async (response) => {
          try {
            const result = await campusOsApi.verifyOnlineOrder(data.institution.id, order.id, response);
            toast.success(result.payment ? `Paid · receipt ${result.payment.receipt.receipt_number}` : "Payment recorded");
          } catch (cause) {
            toast.error(errorMessage(cause, "Payment verification is pending. Refresh; do not pay again."));
          }
          await accounts.refetch();
        },
        onDismiss: async () => {
          try {
            const result = await campusOsApi.reconcileOnlineOrder(data.institution.id, order.id);
            if (result.payment) toast.success(`Paid · receipt ${result.payment.receipt.receipt_number}`);
          } catch {
            /* the order stays open; the webhook or a later reconcile settles it */
          }
          await accounts.refetch();
        },
      });
      return order;
    },
    onError: (cause) => toast.error(errorMessage(cause, "Online payment couldn’t start.")),
  });

  const invoice = useMutation({
    retry: 0,
    mutationFn: async ({ assignment, installmentId }: { assignment: TuitionAssignment; installmentId: number | null }) => {
      const created = await campusOsApi.createInvoice(data.institution.id, assignment.id, installmentId);
      openBlob(await campusOsApi.invoicePdf(data.institution.id, created.id), `invoice-${created.invoice_number}.pdf`);
      return created;
    },
    onError: (cause) => toast.error(errorMessage(cause, "The invoice couldn’t be issued.")),
  });

  const receiptPdf = useMutation({
    mutationFn: async (payment: TuitionPayment) =>
      openBlob(await campusOsApi.receiptPdf(data.institution.id, payment.receipt.id), `receipt-${payment.receipt.receipt_number}.pdf`),
    onError: (cause) => toast.error(errorMessage(cause, "The receipt couldn’t be opened.")),
  });

  return (
    <>
      <div className="campus-os-banner">
        <PageBanner
          eyebrow="My student account"
          title="Fees and receipts, clear for every term."
          description="See what was assessed, what has been paid and what is due next from your protected student ledger."
          share={false}
        />
      </div>
      {accounts.isPending && <CampusOsLoading label="Loading your student fee account" />}
      {accounts.isError && <CampusOsError message="Your fee account couldn’t be loaded." retry={() => void accounts.refetch()} />}
      {accounts.data && !assignments.length && <div className="campus-os-panel"><CampusOsEmpty icon={GraduationCap} title="No fee plan assigned" description="Your institution has not assigned a fee plan to this student account." /></div>}
      {!!assignments.length && !demo && online.isSuccess && !onlineReady && (
        <p className="campus-notice" role="status">Online payment is not set up for this campus yet. Pay at the office or ask them to enable it.</p>
      )}
      {!!assignments.length && (
        <>
          <div className="campus-os-metric-grid">
            <article className="campus-os-metric" data-tone="warning"><div className="campus-os-metric-head"><span>Balance</span><span className="campus-os-metric-icon"><WalletCards size={17} /></span></div><strong>{formatMoney(totalBalance, assignments[0].currency)}</strong><footer>Across {assignments.length} fee {assignments.length === 1 ? "plan" : "plans"}</footer></article>
            <article className="campus-os-metric" data-tone="success"><div className="campus-os-metric-head"><span>Paid</span><span className="campus-os-metric-icon"><CheckCircle2 size={17} /></span></div><strong>{formatMoney(totalPaid, assignments[0].currency)}</strong><footer>Posted to the ledger</footer></article>
            <article className="campus-os-metric" data-tone={nextInstallment?.status === "overdue" ? "danger" : "orange"}><div className="campus-os-metric-head"><span>Next due</span><span className="campus-os-metric-icon"><CalendarClock size={17} /></span></div><strong>{nextInstallment ? formatMoney(nextInstallment.balance, nextInstallment.currency) : "—"}</strong><footer>{nextInstallment ? formatDate(nextInstallment.due_on) : "Nothing outstanding"}</footer></article>
            <article className="campus-os-metric" data-tone="neutral"><div className="campus-os-metric-head"><span>Receipts</span><span className="campus-os-metric-icon"><Receipt size={17} /></span></div><strong>{assignments.reduce((sum, item) => sum + item.payments.length, 0)}</strong><footer>Payment records available</footer></article>
          </div>
          {assignments.map((assignment) => (
            <section className="campus-os-panel" key={assignment.id} aria-labelledby={`student-plan-${assignment.id}`}>
              <header className="campus-os-panel-head"><div><span className="campus-os-section-label">{assignment.plan.academic_year}</span><h2 id={`student-plan-${assignment.id}`}>{assignment.plan.name}</h2><p>{formatMoney(assignment.paid_total, assignment.currency)} paid · {formatMoney(assignment.balance, assignment.currency)} balance</p></div><div className="campus-actions">{assignment.balance > 0 && !demo && <Button size="sm" leftIcon={<CreditCard size={14} />} disabled={!onlineReady} loading={payOnline.isPending && payOnline.variables?.assignment.id === assignment.id && payOnline.variables?.installmentId === null} onClick={() => payOnline.mutate({ assignment, installmentId: null })}>Pay balance</Button>}<CampusOsBadge tone={assignment.balance === 0 ? "success" : "orange"}>{assignment.status}</CampusOsBadge></div></header>
              <div className="campus-os-panel-body">
                <div className="campus-table-wrap"><table className="campus-table campus-os-table"><caption className="sr-only">Installments for {assignment.plan.name}</caption><thead><tr><th>Installment</th><th>Due date</th><th>Amount</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{assignment.installments.map((installment) => <tr key={installment.id}><td>{installment.name}</td><td>{formatDate(installment.due_on)}</td><td>{formatMoney(installment.balance, assignment.currency)}<small>of {formatMoney(installment.amount_due, assignment.currency)}</small></td><td><CampusOsBadge tone={installment.status === "paid" ? "success" : installment.status === "overdue" ? "danger" : "neutral"}>{readable(installment.status)}</CampusOsBadge></td><td>{installment.balance > 0 && !demo && <div className="campus-actions"><Button size="sm" variant="outline" leftIcon={<CreditCard size={14} />} disabled={!onlineReady} aria-label={`Pay online · ${installment.name}`} loading={payOnline.isPending && payOnline.variables?.installmentId === installment.id} onClick={() => payOnline.mutate({ assignment, installmentId: installment.id })}>Pay online</Button><Button size="sm" variant="ghost" leftIcon={<FileText size={14} />} aria-label={`Invoice · ${installment.name}`} loading={invoice.isPending && invoice.variables?.installmentId === installment.id} onClick={() => invoice.mutate({ assignment, installmentId: installment.id })}>Invoice</Button></div>}</td></tr>)}</tbody></table></div>
                {!!assignment.payments.length && <div className="mt-5"><span className="campus-os-section-label">Receipts</span>{assignment.payments.map((payment) => <div className="campus-os-action" key={payment.id}><span className="campus-os-metric-icon"><Receipt size={16} /></span><div><h3>{payment.receipt.receipt_number}</h3><p>{formatDate(payment.paid_at)} · {readable(payment.method)}{payment.reference ? ` · ${payment.reference}` : ""}{payment.received_by ? ` · received by ${payment.received_by.name}` : ""}</p></div><strong>{formatMoney(payment.amount, assignment.currency)}</strong>{!demo && <Button size="sm" variant="ghost" aria-label={`Receipt PDF · ${payment.receipt.receipt_number}`} onClick={() => receiptPdf.mutate(payment)}>Receipt PDF</Button>}</div>)}</div>}
              </div>
            </section>
          ))}
        </>
      )}
    </>
  );
}

export function CampusFinance({ data, role, studentUserId, demo = false }: CampusFinanceProps) {
  const viewerRole = role ?? data.institution.role;
  const canManage = viewerRole === "owner" || viewerRole === "admin";
  return (
    <section className="campus-os" aria-label="Student finance workspace">
      {canManage ? <ManagerFinance data={data} demo={demo} /> : <LearnerFinance data={data} studentUserId={studentUserId} demo={demo} />}
    </section>
  );
}

export default CampusFinance;
