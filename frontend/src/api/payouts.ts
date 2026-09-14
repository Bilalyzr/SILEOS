import { isAxiosError } from "axios";
import { api } from "./axios";

export type WithdrawalStatus = "pending" | "approved" | "rejected" | "paid";

export type WithdrawalMethod =
  | { type: "upi"; upi_id: string }
  | {
      type: "bank";
      account_holder: string;
      account_number: string;
      ifsc: string;
      bank_name?: string;
    };

export interface Withdrawal {
  id: number;
  amount: number;
  method_data: WithdrawalMethod;
  status: WithdrawalStatus;
  reject_detail: string;
  paid_reference: string;
  created_at: string | null;
  processed_at: string | null;
}

export interface InstructorWithdrawals {
  balance: {
    earned: number;
    withdrawn_or_pending: number;
    available: number;
  };
  min_withdrawal_inr: number;
  items: Withdrawal[];
}

export interface AdminWithdrawal extends Withdrawal {
  user_id: number;
  user_email: string;
  display_name: string;
  processed_by: number | null;
}

export const inr = (amount: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(amount);

export function payoutError(error: unknown): string {
  if (isAxiosError<{ detail?: unknown }>(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return "Could not complete this request. Please try again.";
}

export const payoutAPI = {
  mine: () =>
    api
      .get<InstructorWithdrawals>("/instructor/withdrawals")
      .then((response) => response.data),
  request: (amount: number, method_data: WithdrawalMethod) =>
    api
      .post<Withdrawal>("/instructor/withdrawals", { amount, method_data })
      .then((response) => response.data),
  adminList: (status?: WithdrawalStatus) =>
    api
      .get<AdminWithdrawal[]>("/admin/withdrawals", {
        params: status ? { status } : undefined,
      })
      .then((response) => response.data),
  approve: (id: number) =>
    api
      .post<AdminWithdrawal>(`/admin/withdrawals/${id}/approve`)
      .then((response) => response.data),
  reject: (id: number, reject_detail: string) =>
    api
      .post<AdminWithdrawal>(`/admin/withdrawals/${id}/reject`, {
        reject_detail,
      })
      .then((response) => response.data),
  markPaid: (id: number, paid_reference: string) =>
    api
      .post<AdminWithdrawal>(`/admin/withdrawals/${id}/mark-paid`, {
        paid_reference,
      })
      .then((response) => response.data),
};
