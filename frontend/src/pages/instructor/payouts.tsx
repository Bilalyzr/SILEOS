import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowDownToLine, Building2, IndianRupee, WalletCards } from "lucide-react";
import {
  inr,
  payoutAPI,
  payoutError,
  type InstructorWithdrawals,
  type WithdrawalMethod,
} from "@/api/payouts";
import {
  MetricStrip,
  PageHeading,
  PageLayout,
  WorkPanel,
} from "@/components/design-system/PageLayout";
import { Button } from "@/components/ui/button";
import { GlassDialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

type MethodKind = "upi" | "bank";

const EMPTY_FORM = {
  amount: "",
  upi_id: "",
  account_holder: "",
  account_number: "",
  ifsc: "",
  bank_name: "",
};

const badge: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  approved: "bg-blue-100 text-blue-800",
  rejected: "bg-red-100 text-red-800",
  paid: "bg-emerald-100 text-emerald-800",
};

function maskAccount(value = "") {
  return value.length > 4 ? `•••• ${value.slice(-4)}` : "••••";
}

function methodLabel(method: WithdrawalMethod) {
  if (method.type === "upi") return `UPI · ${method.upi_id}`;
  return `${method.bank_name || "Bank transfer"} · ${maskAccount(method.account_number)} · ${method.ifsc}`;
}

export default function InstructorPayoutsPage() {
  const [data, setData] = useState<InstructorWithdrawals>();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [open, setOpen] = useState(false);
  const [method, setMethod] = useState<MethodKind>("upi");
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(await payoutAPI.mine());
    } catch (requestError) {
      setError(payoutError(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const canRequest = useMemo(
    () => !!data && data.balance.available >= data.min_withdrawal_inr,
    [data],
  );

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!data) return;
    const amount = Number(form.amount);
    if (!Number.isFinite(amount) || amount < data.min_withdrawal_inr) {
      setError(`Enter at least ${inr(data.min_withdrawal_inr)}.`);
      return;
    }
    if (amount > data.balance.available) {
      setError(`You can withdraw up to ${inr(data.balance.available)}.`);
      return;
    }
    const methodData: WithdrawalMethod =
      method === "upi"
        ? { type: "upi", upi_id: form.upi_id.trim() }
        : {
            type: "bank",
            account_holder: form.account_holder.trim(),
            account_number: form.account_number.trim(),
            ifsc: form.ifsc.trim().toUpperCase(),
            bank_name: form.bank_name.trim(),
          };
    setSubmitting(true);
    setError("");
    try {
      await payoutAPI.request(amount, methodData);
      setForm(EMPTY_FORM);
      setOpen(false);
      setNotice("Withdrawal request submitted for admin review.");
      await load();
    } catch (requestError) {
      setError(payoutError(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PageLayout
      className="rd-screen rd-screen-instructor-payouts"
      header={
        <PageHeading
          eyebrow="Earnings"
          title="Payouts"
          description="Request a withdrawal from captured course revenue and track manual bank or UPI settlement."
          actions={
            <Button
              onClick={() => {
                setNotice("");
                setError("");
                setOpen(true);
              }}
              disabled={!canRequest || loading}
              leftIcon={<ArrowDownToLine className="h-4 w-4" />}
            >
              Request withdrawal
            </Button>
          }
        />
      }
    >
      {error && !open && (
        <p role="alert" className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-800">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="mb-4 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800">
          {notice}
        </p>
      )}
      <MetricStrip
        items={[
          {
            label: "Earned",
            value: loading ? "—" : inr(data?.balance.earned || 0),
            note: "Completed, non-mock course sales",
          },
          {
            label: "Reserved or paid",
            value: loading ? "—" : inr(data?.balance.withdrawn_or_pending || 0),
            note: "Pending, approved and paid requests",
          },
          {
            label: "Available",
            value: loading ? "—" : inr(data?.balance.available || 0),
            note: data ? `Minimum request ${inr(data.min_withdrawal_inr)}` : "",
          },
        ]}
      />

      <WorkPanel
        title="Withdrawal history"
        description="A paid status means an administrator recorded the external transfer reference."
      >
        {loading ? (
          <p className="text-sm text-slate-600">Loading your payout ledger…</p>
        ) : !data?.items.length ? (
          <div className="py-10 text-center">
            <WalletCards className="mx-auto mb-3 h-10 w-10 text-slate-400" />
            <p className="font-medium text-slate-900">No withdrawal requests yet</p>
            <p className="mt-1 text-sm text-slate-600">
              Eligible captured revenue will appear in your available balance.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-slate-600">
                <tr>
                  <th className="px-3 py-3 font-medium">Requested</th>
                  <th className="px-3 py-3 font-medium">Destination</th>
                  <th className="px-3 py-3 font-medium">Amount</th>
                  <th className="px-3 py-3 font-medium">Status</th>
                  <th className="px-3 py-3 font-medium">Outcome</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <td className="whitespace-nowrap px-3 py-4 text-slate-600">
                      {item.created_at
                        ? new Date(item.created_at).toLocaleDateString("en-IN")
                        : "—"}
                    </td>
                    <td className="px-3 py-4 text-slate-700">{methodLabel(item.method_data)}</td>
                    <td className="whitespace-nowrap px-3 py-4 font-semibold text-slate-950">
                      {inr(item.amount)}
                    </td>
                    <td className="px-3 py-4">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${badge[item.status] || "bg-slate-100"}`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="max-w-xs px-3 py-4 text-slate-600">
                      {item.status === "rejected"
                        ? item.reject_detail || "Rejected by admin"
                        : item.status === "paid"
                          ? `Reference: ${item.paid_reference || "recorded"}`
                          : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </WorkPanel>

      <GlassDialog
        open={open}
        onOpenChange={setOpen}
        title="Request a withdrawal"
        eyebrow="Instructor payout"
        description={data ? `${inr(data.balance.available)} is currently available.` : undefined}
        size="md"
      >
        <form className="space-y-5" onSubmit={submit}>
          {error && (
            <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
              {error}
            </p>
          )}
          <Input
            label="Amount (INR)"
            type="number"
            inputMode="decimal"
            min={data?.min_withdrawal_inr}
            max={data?.balance.available}
            step="0.01"
            required
            value={form.amount}
            onChange={(event) => setForm({ ...form, amount: event.target.value })}
            leftIcon={<IndianRupee className="h-4 w-4" />}
          />
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-slate-700">Payout destination</legend>
            <div className="grid grid-cols-2 gap-3">
              {(["upi", "bank"] as const).map((kind) => (
                <button
                  key={kind}
                  type="button"
                  onClick={() => setMethod(kind)}
                  className={`rounded-xl border p-3 text-left text-sm font-medium ${method === kind ? "border-orange-500 bg-orange-50 text-orange-800" : "border-slate-200 bg-white text-slate-700"}`}
                >
                  {kind === "upi" ? "UPI" : "Bank account"}
                </button>
              ))}
            </div>
          </fieldset>
          {method === "upi" ? (
            <Input
              label="UPI ID"
              placeholder="name@bank"
              required
              pattern="[A-Za-z0-9._-]{2,256}@[A-Za-z]{2,64}"
              value={form.upi_id}
              onChange={(event) => setForm({ ...form, upi_id: event.target.value })}
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Account holder"
                required
                maxLength={120}
                value={form.account_holder}
                onChange={(event) => setForm({ ...form, account_holder: event.target.value })}
              />
              <Input
                label="Bank name"
                maxLength={120}
                value={form.bank_name}
                onChange={(event) => setForm({ ...form, bank_name: event.target.value })}
              />
              <Input
                label="Account number"
                inputMode="numeric"
                required
                pattern="[0-9]{6,20}"
                value={form.account_number}
                onChange={(event) => setForm({ ...form, account_number: event.target.value })}
              />
              <Input
                label="IFSC"
                required
                placeholder="HDFC0001234"
                pattern="[A-Z]{4}0[A-Z0-9]{6}"
                value={form.ifsc}
                onChange={(event) => setForm({ ...form, ifsc: event.target.value.toUpperCase() })}
              />
            </div>
          )}
          <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600">
            <Building2 className="mr-2 inline h-4 w-4" />
            SashaInfinity records the request here; the actual NEFT or UPI transfer is completed externally by finance.
          </div>
          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={submitting}>
              Submit request
            </Button>
          </div>
        </form>
      </GlassDialog>
    </PageLayout>
  );
}
