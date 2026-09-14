import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Parent portal — every approved child's campus signals on one page:
 * attendance, fees, published results, transport, hostel and notices,
 * plus the online-learning digest. Same guardian rules as every campus
 * endpoint: only approved links are shown.
 */
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, BedDouble, Bus, CalendarCheck, CreditCard, FileText, GraduationCap, Heart, Megaphone, UserPlus, WalletCards } from "lucide-react";
import toast from "react-hot-toast";
import { Button } from "@/components/ui/button";
import { api } from "@/api/axios";
import { campusOsApi } from "@/api/campus-os";
import { openBlob } from "@/api/campus-exams";
import { openRazorpay } from "@/lib/razorpayCheckout";
import { parentPortalApi, type PortalInstitution } from "@/api/parent-portal";
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
} from "@/components/institutions/CampusOsPrimitives";
import "@/styles/campus-os.css";

interface DigestCourse {
  course_id: number;
  progress: number;
  status: string;
  risk: { severity: "low" | "medium" | "high"; reasons: string[] } | null;
}
interface Digest {
  student: { id: number; name: string };
  week_of: string;
  courses: DigestCourse[];
}

const ALERT_TONE: Record<string, "danger" | "warning" | "success" | "neutral"> = {
  fees_overdue: "danger",
  attendance_low: "warning",
  transport_not_boarded: "warning",
  hostel_pass_pending: "neutral",
  results_published: "success",
};

export default function ParentDashboard() {
  const [digests, setDigests] = useState<Digest[]>([]);
  const [digestLoading, setDigestLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const portal = useQuery({ queryKey: ["parent-portal"], queryFn: parentPortalApi.overview });

  const loadDigest = () => {
    api
      .get("/parents/digest")
      .then((r) => setDigests(r.data.digests || []))
      .catch(() => toast.error("Failed to load learning digests"))
      .finally(() => setDigestLoading(false));
  };
  useEffect(loadDigest, []);

  async function link() {
    if (!email.trim()) return;
    setBusy(true);
    try {
      const r = await api.post("/parents/children", { email: email.trim() });
      toast.success(r.data.already ? "Already linked" : "Access request sent. The student must approve it.");
      setEmail("");
      loadDigest();
      void portal.refetch();
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Link failed");
    } finally {
      setBusy(false);
    }
  }

  const sevColor = {
    high: "bg-red-100 text-red-700",
    medium: "bg-amber-100 text-amber-700",
    low: "bg-gray-100 text-gray-600",
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="dash-h1 flex items-center gap-2">
              <Heart className="h-7 w-7 text-primary" /> Your children
            </h1>
            <p className="text-slate-600 text-sm mt-1 mb-6">
              Attendance, fees, results, transport, hostel and notices for every child in one place.
            </p>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-parent-dashboard campus-os"
    >
      <div className="flex gap-2 mb-8">
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Request access using the student’s email…"
          aria-label="Student email"
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
        />
        <Button onClick={link} disabled={busy || !email.trim()}>
          <UserPlus className="h-4 w-4 mr-1" /> Request access
        </Button>
      </div>

      {portal.isPending && <CampusOsLoading label="Loading your children’s campus summary" />}
      {portal.isError && <CampusOsError message="The campus summary couldn’t be loaded." retry={() => void portal.refetch()} />}
      {portal.data && portal.data.pending_requests > 0 && (
        <p className="campus-notice mb-4" role="status">
          {portal.data.pending_requests} access request{portal.data.pending_requests === 1 ? "" : "s"} waiting for the student to approve.
        </p>
      )}
      {portal.data && !portal.data.children.length && (
        <CampusOsEmpty title="No children linked yet" description="Request access with the student’s email. They approve it from their dashboard." />
      )}
      {portal.data?.children.map((child) => (
        <section key={child.student.id} className="campus-panel mb-6" aria-label={`${child.student.name} campus summary`}>
          <div className="campus-panel-heading">
            <div>
              <h2>{child.student.name}</h2>
              <p className="campus-muted">{child.student.email}</p>
            </div>
          </div>
          {!child.institutions.length && <p className="campus-muted">Not enrolled in a campus yet. Online learning appears below.</p>}
          {child.institutions.map((block) => (
            <InstitutionCard key={block.institution.id} block={block} onPaid={() => void portal.refetch()} />
          ))}
        </section>
      ))}

      <section className="campus-panel">
        <h2>Online learning</h2>
        <p className="campus-muted mb-3">Weekly course progress and where your child needs help.</p>
        {digestLoading ? (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className="h-16 rounded-xl bg-gray-100 animate-pulse" />
            ))}
          </div>
        ) : digests.length === 0 ? (
          <p className="text-gray-500 text-sm">No course activity yet.</p>
        ) : (
          <div className="space-y-4">
            {digests.map((d) => (
              <div key={d.student.id}>
                <h3 className="font-semibold text-gray-900">{d.student.name}</h3>
                <p className="text-xs text-gray-400 mb-2">Week of {d.week_of}</p>
                {d.courses.length === 0 ? (
                  <p className="text-sm text-gray-500">Not enrolled in any course.</p>
                ) : (
                  <ul className="space-y-2">
                    {d.courses.map((c) => (
                      <li key={c.course_id} className="flex flex-wrap items-center gap-3 text-sm bg-gray-50 rounded-lg px-3 py-2">
                        <span className="font-medium text-gray-800">Course #{c.course_id}</span>
                        <span className="text-gray-500">
                          {c.progress}% complete · {c.status}
                        </span>
                        {c.risk && <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${sevColor[c.risk.severity]}`}>needs attention</span>}
                        {c.risk && <span className="text-xs text-gray-500 w-full">{c.risk.reasons[0]}</span>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </PageLayout>
  );
}

function InstitutionCard({ block, onPaid }: { block: PortalInstitution; onPaid: () => void }) {
  const fees = block.fees;
  const currency = fees?.currency ?? "INR";
  const institutionId = block.institution.id;
  const payable = Boolean(fees && fees.outstanding > 0 && fees.assignment_id);

  const payNow = useMutation({
    retry: 0,
    mutationFn: async () => {
      if (!fees?.assignment_id || !fees.next_due) throw new Error("Nothing is due.");
      const { order, checkout } = await campusOsApi.createOnlineOrder(institutionId, fees.assignment_id, { installment_id: fees.next_due.installment_id, amount: null });
      await openRazorpay(checkout, {
        onSuccess: async (response) => {
          try {
            const result = await campusOsApi.verifyOnlineOrder(institutionId, order.id, response);
            toast.success(result.payment ? `Paid · receipt ${result.payment.receipt.receipt_number}` : "Payment recorded");
          } catch (cause) {
            toast.error(errorMessage(cause, "Payment verification is pending. Refresh; do not pay again."));
          }
          onPaid();
        },
        onDismiss: async () => {
          try {
            await campusOsApi.reconcileOnlineOrder(institutionId, order.id);
          } catch {
            /* stays open until the webhook or a later reconcile settles it */
          }
          onPaid();
        },
      });
      return order;
    },
    onError: (cause) => toast.error(errorMessage(cause, "Online payment couldn’t start.")),
  });

  const invoice = useMutation({
    retry: 0,
    mutationFn: async () => {
      if (!fees?.assignment_id) throw new Error("Nothing is due.");
      const created = await campusOsApi.createInvoice(institutionId, fees.assignment_id, null);
      openBlob(await campusOsApi.invoicePdf(institutionId, created.id), `invoice-${created.invoice_number}.pdf`);
      return created;
    },
    onError: (cause) => toast.error(errorMessage(cause, "The invoice couldn’t be issued.")),
  });

  return (
    <article className="campus-os-panel mb-4">
      <header className="campus-os-panel-head">
        <div>
          <span className="campus-os-section-label">{block.institution.academic_year}</span>
          <h3>{block.institution.name}</h3>
          <p>{block.batches.join(" · ") || "No batch yet"}</p>
        </div>
        <GraduationCap size={20} color="#a9360c" aria-hidden="true" />
      </header>
      <div className="campus-os-panel-body">
        {!!block.alerts.length && (
          <ul className="campus-actions mb-3" aria-label="Alerts">
            {block.alerts.map((alert) => (
              <li key={alert.kind}>
                <span className="campus-chip" data-tone={ALERT_TONE[alert.kind] ?? "neutral"}>
                  <AlertTriangle size={12} className="mr-1 inline" aria-hidden="true" />
                  {alert.message}
                </span>
              </li>
            ))}
          </ul>
        )}
        <div className="campus-os-metric-grid">
          <article className="campus-os-metric" data-tone={block.attendance && block.attendance.percent < 75 ? "warning" : "success"}>
            <div className="campus-os-metric-head">
              <span>Attendance (30 days)</span>
              <span className="campus-os-metric-icon">
                <CalendarCheck size={17} />
              </span>
            </div>
            <strong>{block.attendance ? `${block.attendance.percent}%` : "—"}</strong>
            <footer>{block.attendance ? `${block.attendance.present} of ${block.attendance.total} days present` : "Not recorded yet"}</footer>
          </article>
          <article className="campus-os-metric" data-tone={fees && fees.overdue > 0 ? "danger" : "orange"}>
            <div className="campus-os-metric-head">
              <span>Fees outstanding</span>
              <span className="campus-os-metric-icon">
                <WalletCards size={17} />
              </span>
            </div>
            <strong>{fees ? formatMoney(fees.outstanding, currency) : "—"}</strong>
            <footer>
              {fees ? (fees.overdue > 0 ? `${formatMoney(fees.overdue, currency)} overdue` : fees.next_due ? `Next: ${fees.next_due.name} on ${formatDate(fees.next_due.due_on)}` : "Nothing due") : "No fee account"}
            </footer>
            {payable && (
              <div className="campus-actions mt-2">
                <Button size="sm" leftIcon={<CreditCard size={14} />} loading={payNow.isPending} onClick={() => payNow.mutate()}>Pay now</Button>
                <Button size="sm" variant="ghost" leftIcon={<FileText size={14} />} loading={invoice.isPending} onClick={() => invoice.mutate()}>Invoice</Button>
              </div>
            )}
          </article>
          <article className="campus-os-metric" data-tone="orange">
            <div className="campus-os-metric-head">
              <span>Transport today</span>
              <span className="campus-os-metric-icon">
                <Bus size={17} />
              </span>
            </div>
            <strong>
              {block.transport?.assigned ? (block.transport.today ? (block.transport.today.boarded ? "Boarded" : "Not boarded") : "Not recorded") : "—"}
            </strong>
            <footer>{block.transport?.assigned ? `${block.transport.route?.name} · ${block.transport.stop?.name ?? ""}` : "No transport assigned"}</footer>
          </article>
          <article className="campus-os-metric" data-tone="orange">
            <div className="campus-os-metric-head">
              <span>Hostel</span>
              <span className="campus-os-metric-icon">
                <BedDouble size={17} />
              </span>
            </div>
            <strong>{block.hostel?.resident ? `${block.hostel.block} · ${block.hostel.room}` : "—"}</strong>
            <footer>
              {block.hostel?.pending_pass
                ? "Out-pass waiting for approval"
                : block.hostel?.approved_pass
                  ? `Out-pass approved · leaves ${formatDate(block.hostel.approved_pass.leaves_at)} ${formatTime(block.hostel.approved_pass.leaves_at)}`
                  : block.hostel?.resident
                    ? "In residence"
                    : "Day scholar"}
            </footer>
          </article>
        </div>
        <div className="campus-os-columns mt-4">
          <div>
            <h4 className="font-semibold text-stone-800">Latest results</h4>
            {!block.exams.length ? (
              <p className="campus-muted">No published results yet.</p>
            ) : (
              <ul className="campus-activity">
                {block.exams.map((exam) => (
                  <li key={exam.id}>
                    <strong>{exam.name}</strong> · {exam.total} / {exam.max_total} ({exam.percent ?? "—"}%) · rank {exam.rank} of {exam.students}{" "}
                    <CampusOsBadge tone={exam.passed ? "success" : "warning"}>{exam.passed ? "Pass" : "Fail"}</CampusOsBadge>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <h4 className="font-semibold text-stone-800">
              <Megaphone size={14} className="mr-1 inline" aria-hidden="true" />
              Notices
            </h4>
            {!block.notices.length ? (
              <p className="campus-muted">No notices yet.</p>
            ) : (
              <ul className="campus-activity">
                {block.notices.map((notice) => (
                  <li key={notice.id}>
                    <strong>{notice.title}</strong>
                    {notice.created_at && <small> · {formatDate(notice.created_at)}</small>}
                    <p className="campus-muted">{notice.body}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
        {block.transport?.assigned && block.transport.route && (
          <p className="campus-muted mt-3 text-xs">
            {readable("transport")}: {[block.transport.route.vehicle_number, block.transport.route.driver_name, block.transport.route.driver_phone].filter(Boolean).join(" · ") || "Vehicle details to follow"}
          </p>
        )}
      </div>
    </article>
  );
}
