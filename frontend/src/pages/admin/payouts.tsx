import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Clock3, Landmark, RefreshCw } from "lucide-react";
import {
  inr,
  payoutAPI,
  payoutError,
  type AdminWithdrawal,
  type WithdrawalMethod,
  type WithdrawalStatus,
} from "@/api/payouts";
import {
  MetricStrip,
  PageHeading,
  PageLayout,
  WorkPanel,
} from "@/components/design-system/PageLayout";
import { Button } from "@/components/ui/button";
import { useConfirm } from "@/components/ui/confirm";

const statuses: Array<WithdrawalStatus | "all"> = [
  "pending",
  "approved",
  "paid",
  "rejected",
  "all",
];

const badge: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  approved: "bg-blue-100 text-blue-800",
  rejected: "bg-red-100 text-red-800",
  paid: "bg-emerald-100 text-emerald-800",
};

function maskAccount(value = "") {
  return value.length > 4 ? `•••• ${value.slice(-4)}` : "••••";
}

function destination(method: WithdrawalMethod) {
  if (method.type === "upi") return `UPI · ${method.upi_id}`;
  return [
    method.account_holder,
    method.bank_name || "Bank transfer",
    maskAccount(method.account_number),
    method.ifsc,
  ].join(" · ");
}

export default function AdminPayoutsPage() {
  const confirm = useConfirm();
  const [filter, setFilter] = useState<WithdrawalStatus | "all">("pending");
  const [items, setItems] = useState<AdminWithdrawal[]>([]);
  const [loading, setLoading] = useState(true);
  const [workingId, setWorkingId] = useState<number>();
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setItems(await payoutAPI.adminList(filter === "all" ? undefined : filter));
    } catch (requestError) {
      setError(payoutError(requestError));
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async (id: number, action: () => Promise<unknown>) => {
    setWorkingId(id);
    setError("");
    try {
      await action();
      await load();
    } catch (requestError) {
      setError(payoutError(requestError));
    } finally {
      setWorkingId(undefined);
    }
  };

  const approve = async (item: AdminWithdrawal) => {
    const ok = await confirm({
      eyebrow: "Payout control",
      title: `Approve ${inr(item.amount)}?`,
      body: `This reserves the request for ${item.display_name || item.user_email}. Finance must still transfer the money externally.`,
      confirmLabel: "Approve request",
    });
    if (ok) void run(item.id, () => payoutAPI.approve(item.id));
  };

  const reject = async (item: AdminWithdrawal) => {
    const reason = await confirm.prompt({
      eyebrow: "Payout control",
      title: "Reject withdrawal request",
      body: "Give the instructor a clear reason. Rejection releases the amount back to their available balance.",
      placeholder: "Reason for rejection",
      confirmLabel: "Reject request",
      danger: true,
      multiline: true,
      required: true,
    });
    if (reason?.trim()) {
      void run(item.id, () => payoutAPI.reject(item.id, reason.trim()));
    }
  };

  const markPaid = async (item: AdminWithdrawal) => {
    const reference = await confirm.prompt({
      eyebrow: "External settlement",
      title: "Record payout as paid",
      body: "Enter the bank UTR or UPI transaction reference only after finance completes the transfer.",
      placeholder: "UTR / UPI reference",
      confirmLabel: "Mark paid",
      required: true,
    });
    if (reference?.trim()) {
      void run(item.id, () => payoutAPI.markPaid(item.id, reference.trim()));
    }
  };

  const total = items.reduce((sum, item) => sum + item.amount, 0);

  return (
    <PageLayout
      className="rd-screen rd-screen-admin-payouts"
      header={
        <PageHeading
          eyebrow="Commerce · Money operations"
          title="Instructor payouts"
          description="Review withdrawal requests, record approvals, and reconcile manual NEFT or UPI settlements."
          actions={
            <Button
              variant="outline"
              onClick={() => void load()}
              disabled={loading}
              leftIcon={<RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />}
            >
              Refresh
            </Button>
          }
        />
      }
      toolbar={
        <label className="flex items-center gap-3 text-sm font-medium text-slate-700">
          Queue
          <select
            className="sf-input min-w-40"
            value={filter}
            onChange={(event) => setFilter(event.target.value as WithdrawalStatus | "all")}
          >
            {statuses.map((status) => (
              <option key={status} value={status}>
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </option>
            ))}
          </select>
        </label>
      }
    >
      {error && (
        <p role="alert" className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-800">
          {error}
        </p>
      )}
      <MetricStrip
        items={[
          { label: "Requests in view", value: loading ? "—" : items.length },
          { label: "Value in view", value: loading ? "—" : inr(total) },
          {
            label: "Settlement mode",
            value: "Manual",
            note: "NEFT or UPI, recorded with reference",
          },
        ]}
      />
      <WorkPanel
        title={`${filter === "all" ? "All" : filter.charAt(0).toUpperCase() + filter.slice(1)} requests`}
        description="State changes are one-way and stored in the central audit trail. Full account numbers stay masked."
      >
        {loading ? (
          <p className="text-sm text-slate-600">Loading payout queue…</p>
        ) : !items.length ? (
          <div className="py-12 text-center">
            <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-emerald-500" />
            <p className="font-medium text-slate-900">This queue is clear</p>
            <p className="mt-1 text-sm text-slate-600">There are no {filter === "all" ? "withdrawal" : filter} requests.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-slate-600">
                <tr>
                  <th className="px-3 py-3 font-medium">Instructor</th>
                  <th className="px-3 py-3 font-medium">Destination</th>
                  <th className="px-3 py-3 font-medium">Amount</th>
                  <th className="px-3 py-3 font-medium">Status</th>
                  <th className="px-3 py-3 font-medium">Requested</th>
                  <th className="px-3 py-3 text-right font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-3 py-4">
                      <p className="font-medium text-slate-950">{item.display_name || "Unnamed instructor"}</p>
                      <p className="text-xs text-slate-600">{item.user_email}</p>
                    </td>
                    <td className="max-w-sm px-3 py-4 text-slate-700">{destination(item.method_data)}</td>
                    <td className="whitespace-nowrap px-3 py-4 font-semibold text-slate-950">{inr(item.amount)}</td>
                    <td className="px-3 py-4">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${badge[item.status] || "bg-slate-100"}`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-slate-600">
                      <Clock3 className="mr-1 inline h-3.5 w-3.5" />
                      {item.created_at ? new Date(item.created_at).toLocaleDateString("en-IN") : "—"}
                    </td>
                    <td className="px-3 py-4">
                      <div className="flex justify-end gap-2">
                        {item.status === "pending" && (
                          <>
                            <Button size="sm" variant="outline" disabled={workingId === item.id} onClick={() => void reject(item)}>
                              Reject
                            </Button>
                            <Button size="sm" loading={workingId === item.id} onClick={() => void approve(item)}>
                              Approve
                            </Button>
                          </>
                        )}
                        {item.status === "approved" && (
                          <Button
                            size="sm"
                            loading={workingId === item.id}
                            leftIcon={<Landmark className="h-4 w-4" />}
                            onClick={() => void markPaid(item)}
                          >
                            Mark paid
                          </Button>
                        )}
                        {item.status === "rejected" && (
                          <span className="max-w-xs text-right text-xs text-slate-600">{item.reject_detail}</span>
                        )}
                        {item.status === "paid" && (
                          <span className="max-w-xs text-right text-xs text-slate-600">Ref: {item.paid_reference}</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </WorkPanel>
    </PageLayout>
  );
}
