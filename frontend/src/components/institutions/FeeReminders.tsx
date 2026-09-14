import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, RefreshCw } from "lucide-react";
import toast from "react-hot-toast";
import {
  remindersApi,
  type ReminderChannel,
  type ReminderPolicy,
  type ReminderPolicyInput,
  type ReminderRow,
  type ReminderStatus,
  type RunResult,
} from "@/api/tuition-reminders";
import { Button } from "@/components/ui/button";
import {
  CampusOsBadge,
  CampusOsEmpty,
  CampusOsError,
  CampusOsLoading,
  errorMessage,
  formatDate,
  formatMoney,
  readable,
} from "./CampusOsPrimitives";

const STATUS_TONE: Record<ReminderStatus, "success" | "warning" | "danger" | "neutral"> = {
  sent: "success",
  queued: "warning",
  failed: "danger",
  skipped: "neutral",
};

export const REASONS: Record<string, string> = {
  whatsapp_not_configured: "WhatsApp is not configured",
  email_not_configured: "Email is not configured",
  no_consent: "No WhatsApp consent",
  not_a_member: "Not a campus member",
  no_email: "No email address",
  no_channel: "No channel available",
};

function parseDays(value: string) {
  return Array.from(
    new Set(
      value
        .split(/[,\s]+/)
        .map((part) => part.trim())
        .filter(Boolean)
        .map(Number)
        .filter((n) => Number.isInteger(n) && n >= 0 && n <= 60),
    ),
  ).sort((a, b) => b - a);
}

export function FeeReminders({ institutionId }: { institutionId: number }) {
  const queryClient = useQueryClient();
  const policy = useQuery({
    queryKey: ["fee-reminders", institutionId, "policy"],
    queryFn: () => remindersApi.policy(institutionId),
  });
  const [status, setStatus] = useState<ReminderStatus | "">("");
  const log = useQuery({
    queryKey: ["fee-reminders", institutionId, "log", status],
    queryFn: () => remindersApi.list(institutionId, status ? { status } : {}),
  });
  const [form, setForm] = useState<ReminderPolicyInput | null>(null);
  const [days, setDays] = useState("");
  const [result, setResult] = useState<RunResult | null>(null);
  useEffect(() => {
    if (policy.data && form === null) {
      const { institution_id: _id, updated_at: _at, ...rest } = policy.data;
      setForm(rest);
      setDays(rest.days_before.join(", "));
    }
  }, [policy.data, form]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["fee-reminders", institutionId] });
  const save = useMutation({
    mutationFn: (input: ReminderPolicyInput) => remindersApi.savePolicy(institutionId, input),
    onSuccess: (saved: ReminderPolicy) => {
      const { institution_id: _id, updated_at: _at, ...rest } = saved;
      setForm(rest);
      setDays(rest.days_before.join(", "));
      toast.success("Reminder policy saved");
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "The reminder policy couldn’t be saved.")),
  });
  const run = useMutation({
    mutationFn: () => remindersApi.runNow(institutionId),
    onSuccess: (counts) => {
      setResult(counts);
      toast.success(`Reminders run: ${counts.sent} sent, ${counts.failed} failed, ${counts.skipped} skipped`);
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "Reminders couldn’t be run.")),
  });
  const retry = useMutation({
    mutationFn: (reminderId: number) => remindersApi.retry(institutionId, reminderId),
    onSuccess: (row: ReminderRow) => {
      toast[row.status === "sent" ? "success" : "error"](row.status === "sent" ? "Reminder sent" : row.error || "Retry failed");
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "The reminder couldn’t be retried.")),
  });

  function toggleChannel(channel: ReminderChannel) {
    if (!form) return;
    const next = form.channels.includes(channel)
      ? form.channels.filter((c) => c !== channel)
      : [...form.channels, channel];
    setForm({ ...form, channels: next });
  }

  return (
    <section className="campus-os-panel" aria-labelledby="fee-reminders-title">
      <header className="campus-os-panel-head">
        <div>
          <span className="campus-os-section-label">Collections</span>
          <h2 id="fee-reminders-title">Fee reminders</h2>
          <p>Automatic due-date and overdue notices over WhatsApp and email, plus receipts after every payment.</p>
        </div>
        <BellRing size={20} color="#a9360c" aria-hidden="true" />
      </header>
      <div className="campus-os-panel-body pt-4">
        {policy.isPending && <CampusOsLoading label="Loading reminder policy" />}
        {policy.isError && <CampusOsError message="The reminder policy couldn’t be loaded." retry={() => void policy.refetch()} />}
        {form && (
          <form
            className="campus-form"
            onSubmit={(event) => {
              event.preventDefault();
              const parsed = parseDays(days);
              if (!parsed.length) {
                toast.error("Enter at least one day-before value between 0 and 60.");
                return;
              }
              if (!form.channels.length) {
                toast.error("Choose at least one channel.");
                return;
              }
              save.mutate({ ...form, days_before: parsed.slice(0, 5) });
            }}
          >
            <div className="flex items-center gap-2 text-sm font-semibold text-stone-800">
              <input
                id="fee-reminders-enabled"
                type="checkbox"
                className="campus-check"
                checked={form.enabled}
                onChange={(event) => setForm({ ...form, enabled: event.target.checked })}
              />
              <label htmlFor="fee-reminders-enabled" className="m-0">Send reminders automatically</label>
            </div>
            <div className="campus-form-grid">
              <label>
                Days before due date
                <input
                  aria-label="Days before due date"
                  value={days}
                  placeholder="7, 1"
                  onChange={(event) => setDays(event.target.value)}
                />
              </label>
              <label>
                Overdue repeat (days)
                <input
                  aria-label="Overdue repeat days"
                  type="number"
                  min={1}
                  max={30}
                  value={form.overdue_every_days}
                  onChange={(event) => setForm({ ...form, overdue_every_days: Number(event.target.value) })}
                />
              </label>
              <label>
                Overdue reminders (max)
                <input
                  aria-label="Overdue reminders maximum"
                  type="number"
                  min={0}
                  max={12}
                  value={form.overdue_max}
                  onChange={(event) => setForm({ ...form, overdue_max: Number(event.target.value) })}
                />
              </label>
              <label>
                Send hour (campus time)
                <input
                  aria-label="Send hour"
                  type="number"
                  min={0}
                  max={23}
                  value={form.send_hour}
                  onChange={(event) => setForm({ ...form, send_hour: Number(event.target.value) })}
                />
              </label>
            </div>
            <fieldset className="campus-panel p-4">
              <legend className="px-2 text-sm font-bold text-stone-800">Channels</legend>
              <div className="campus-actions">
                {(["whatsapp", "email"] as ReminderChannel[]).map((channel) => (
                  <div key={channel} className="flex items-center gap-2 text-sm">
                    <input
                      id={`fee-reminders-channel-${channel}`}
                      type="checkbox"
                      className="campus-check"
                      aria-label={`Channel ${channel}`}
                      checked={form.channels.includes(channel)}
                      onChange={() => toggleChannel(channel)}
                    />
                    <label htmlFor={`fee-reminders-channel-${channel}`} className="m-0">
                      {channel === "whatsapp" ? "WhatsApp (consented members)" : "Email"}
                    </label>
                  </div>
                ))}
              </div>
              <div className="campus-form-grid mt-3">
                <label>
                  WhatsApp template name
                  <input
                    aria-label="WhatsApp template name"
                    value={form.whatsapp_template}
                    maxLength={120}
                    placeholder="fee_reminder"
                    onChange={(event) => setForm({ ...form, whatsapp_template: event.target.value })}
                  />
                </label>
                <label>
                  Template language
                  <input
                    aria-label="Template language"
                    value={form.whatsapp_language}
                    maxLength={20}
                    onChange={(event) => setForm({ ...form, whatsapp_language: event.target.value })}
                  />
                </label>
              </div>
              <p className="campus-muted mt-2 text-xs">
                WhatsApp goes only to campus members who confirmed consent, using an approved template. Everyone else falls back to email.
              </p>
            </fieldset>
            <div className="flex flex-wrap justify-end gap-2">
              <Button type="button" variant="outline" leftIcon={<RefreshCw size={14} />} loading={run.isPending} onClick={() => run.mutate()}>
                Run now
              </Button>
              <Button type="submit" loading={save.isPending}>
                Save policy
              </Button>
            </div>
            {result && (
              <p className="campus-notice" role="status">
                Last run: {result.staged} staged · {result.sent} sent · {result.failed} failed · {result.skipped} skipped
              </p>
            )}
          </form>
        )}

        <div className="campus-os-toolbar mt-4">
          <span className="campus-os-section-label">Delivery log</span>
          <label className="flex items-center gap-2 text-xs font-semibold text-stone-600">
            Status
            <select
              className="campus-os-control"
              aria-label="Filter reminders by status"
              value={status}
              onChange={(event) => setStatus(event.target.value as ReminderStatus | "")}
            >
              <option value="">All</option>
              <option value="queued">Queued</option>
              <option value="sent">Sent</option>
              <option value="failed">Failed</option>
              <option value="skipped">Skipped</option>
            </select>
          </label>
        </div>
        {log.isPending && <CampusOsLoading label="Loading reminder log" />}
        {log.isError && <CampusOsError message="The reminder log couldn’t be loaded." retry={() => void log.refetch()} />}
        {log.data && !log.data.items.length && (
          <CampusOsEmpty title="No reminders yet" description="Enable the policy or run it now to stage today’s reminders." />
        )}
        {!!log.data?.items.length && (
          <div className="campus-table-wrap">
            <table className="campus-table campus-os-table">
              <caption className="sr-only">Fee reminder deliveries</caption>
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Recipient</th>
                  <th>Reminder</th>
                  <th className="campus-os-hide-mobile">Amount</th>
                  <th>Channel</th>
                  <th>Status</th>
                  <th><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {log.data.items.map((row) => (
                  <tr key={row.id}>
                    <td>{row.student_name}</td>
                    <td>
                      {row.recipient_name || "—"}
                      <small>{readable(row.recipient_role)}</small>
                    </td>
                    <td>
                      {readable(row.kind)}
                      <small>{row.due_on ? `Due ${formatDate(row.due_on)}` : row.stage}</small>
                    </td>
                    <td className="campus-os-hide-mobile">{formatMoney(row.amount, row.currency)}</td>
                    <td>{row.channel === "whatsapp" ? "WhatsApp" : "Email"}</td>
                    <td>
                      <CampusOsBadge tone={STATUS_TONE[row.status]}>{readable(row.status)}</CampusOsBadge>
                      {row.skip_reason && <small>{REASONS[row.skip_reason] ?? readable(row.skip_reason)}</small>}
                      {row.error && <small>{row.error}</small>}
                    </td>
                    <td>
                      {row.status === "failed" && (
                        <Button size="sm" variant="outline" loading={retry.isPending} onClick={() => retry.mutate(row.id)}>
                          Retry
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
