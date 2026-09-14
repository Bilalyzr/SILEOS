/**
 * Razorpay checkout loader shared by the fee pages. The script is loaded on
 * demand so pages that never pay carry no third-party code.
 */
import type { OnlineCheckout } from "@/api/campus-os";

export interface RazorpayResponse {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

const SDK = "https://checkout.razorpay.com/v1/checkout.js";

type RazorpayWindow = Window & { Razorpay?: new (options: Record<string, unknown>) => { open: () => void } };

export async function ensureRazorpayLoaded(): Promise<void> {
  const w = window as RazorpayWindow;
  if (w.Razorpay) return;
  await new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${SDK}"]`);
    if (existing) {
      if (w.Razorpay) return resolve();
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("Failed to load Razorpay SDK")));
      return;
    }
    const script = document.createElement("script");
    script.src = SDK;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Razorpay SDK"));
    document.body.appendChild(script);
  });
  if (!w.Razorpay) {
    throw new Error("Razorpay SDK did not initialize. Disable ad-blockers and retry.");
  }
}

export async function openRazorpay(
  checkout: OnlineCheckout,
  handlers: { onSuccess: (response: RazorpayResponse) => void; onDismiss: () => void },
): Promise<void> {
  await ensureRazorpayLoaded();
  const Razorpay = (window as RazorpayWindow).Razorpay!;
  const instance = new Razorpay({
    key: checkout.key,
    amount: checkout.amount_paise,
    currency: checkout.currency,
    name: checkout.name,
    description: checkout.description,
    order_id: checkout.order_id,
    prefill: checkout.prefill,
    handler: handlers.onSuccess,
    modal: { ondismiss: handlers.onDismiss },
    theme: { color: "#a9360c" },
  });
  instance.open();
}
