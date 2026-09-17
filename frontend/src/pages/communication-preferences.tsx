import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bell,
  CheckCircle2,
  ExternalLink,
  LockKeyhole,
  MessageCircle,
  ShieldCheck,
  Smartphone,
} from "lucide-react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { whatsappApi, type WhatsAppAccountStatus } from "@/api/whatsapp";
import { BrandBanner } from "@/components/design-system/BrandBanner";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth";

function readableError(cause: unknown) {
  const error = cause as {
    response?: { data?: { detail?: string } };
    message?: string;
  };
  return error.response?.data?.detail || error.message || "Please try again.";
}

function friendlyDate(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}

const STATE_COPY = {
  not_started: {
    label: "Not connected",
    copy: "Add your number when you want useful SashaInfinity updates on WhatsApp.",
  },
  pending: {
    label: "Waiting for confirmation",
    copy: "Open WhatsApp and send the prepared JOIN message from your own account.",
  },
  confirmed: {
    label: "Connected",
    copy: "Your permission is active. Only approved SashaInfinity messages can be sent.",
  },
  revoked: {
    label: "Permission withdrawn",
    copy: "WhatsApp updates are off. You can reconnect whenever you choose.",
  },
} as const;

export function WhatsAppPreferenceCard() {
  const query = useQuery({
    queryKey: ["whatsapp-account-status"],
    queryFn: whatsappApi.status,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pendingUrl, setPendingUrl] = useState<string | null>(null);

  async function submitOptIn(form: HTMLFormElement) {
    const fields = new FormData(form);
    const phone = String(fields.get("phone") || "").trim();
    setBusy(true);
    setError("");
    try {
      const result = await whatsappApi.optIn(phone);
      setPendingUrl(result.click_to_chat_url);
      await query.refetch();
      toast.success(
        result.status === "confirmed"
          ? "WhatsApp updates are connected."
          : "Open WhatsApp to confirm your number.",
      );
    } catch (cause) {
      setError(readableError(cause));
    } finally {
      setBusy(false);
    }
  }

  async function optOut() {
    setBusy(true);
    setError("");
    try {
      await whatsappApi.optOut();
      setPendingUrl(null);
      await query.refetch();
      toast.success("WhatsApp permission withdrawn.");
    } catch (cause) {
      setError(readableError(cause));
    } finally {
      setBusy(false);
    }
  }

  if (query.isLoading) {
    return (
      <section className="campus-panel" aria-label="Loading WhatsApp preferences">
        <div className="campus-skeleton" role="status" />
      </section>
    );
  }

  if (query.isError || !query.data) {
    return (
      <section className="campus-panel">
        <div className="campus-error" role="alert">
          WhatsApp preferences could not be loaded. {" "}
          <button type="button" onClick={() => void query.refetch()}>
            Retry
          </button>
        </div>
      </section>
    );
  }

  const status: WhatsAppAccountStatus = query.data;
  const available =
    status.configured &&
    status.business_phone_configured &&
    status.webhook_ready;
  const joinUrl = pendingUrl || status.join_url;
  const joined = status.contact_status === "confirmed" || status.opted_in;
  const displayState = pendingUrl && !joined ? "pending" : status.contact_status;
  const state = STATE_COPY[displayState];
  const canWithdraw = joined || displayState === "pending";

  return (
    <section className="campus-panel overflow-hidden">
      <div className="campus-panel-heading">
        <div>
          <span className="campus-eyebrow">
            <MessageCircle size={14} /> WhatsApp
          </span>
          <h2 className="mt-2 text-xl font-bold text-secondary-900">
            SashaInfinity updates on your phone
          </h2>
          <p className="campus-muted mt-2 max-w-2xl">
            One preference follows your account across courses, learning labs,
            campus workspaces and SashaInfinity services.
          </p>
        </div>
        <span
          className="campus-chip"
          data-tone={joined ? "success" : "muted"}
        >
          {state.label}
        </span>
      </div>

      {!available && (
        <div className="campus-notice mt-5">
          <strong>WhatsApp updates are being connected.</strong>
          <p className="mt-2">
            Your in-app notifications still work. You can add WhatsApp as soon
            as the official SashaInfinity business number is ready.
          </p>
        </div>
      )}

      {error && (
        <p className="campus-error mt-5" role="alert">
          {error}
        </p>
      )}

      <div className="mt-5 grid gap-4 md:grid-cols-[minmax(0,1.4fr)_minmax(240px,0.6fr)]">
        <div className="rounded-2xl border border-orange-100 bg-orange-50/55 p-5">
          <div className="flex items-start gap-3">
            <span className="campus-icon">
              {joined ? <CheckCircle2 size={19} /> : <Smartphone size={19} />}
            </span>
            <div>
              <strong className="text-secondary-900">{state.label}</strong>
              <p className="campus-muted mt-1">{state.copy}</p>
              {status.phone && (
                <p className="mt-3 text-sm font-semibold text-secondary-800">
                  {status.phone}
                </p>
              )}
              {status.consent_at && joined && (
                <p className="campus-muted mt-1">
                  Confirmed {friendlyDate(status.consent_at)}
                </p>
              )}
            </div>
          </div>

          {displayState === "pending" && joinUrl && (
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <Button asChild>
                <a href={joinUrl} target="_blank" rel="noreferrer">
                  Open WhatsApp to confirm
                  <ExternalLink className="ml-2 h-4 w-4" />
                </a>
              </Button>
              {status.join_expires_at && (
                <span className="campus-muted">
                  Link expires {friendlyDate(status.join_expires_at)}
                </span>
              )}
            </div>
          )}

          {canWithdraw && (
            <Button
              className="mt-5"
              variant="outline"
              loading={busy}
              onClick={() => void optOut()}
            >
              Turn off WhatsApp updates
            </Button>
          )}
        </div>

        <div className="rounded-2xl border border-white bg-white/75 p-5 shadow-sm">
          <div className="flex items-center gap-2 font-semibold text-secondary-900">
            <ShieldCheck className="h-5 w-5 text-orange-600" /> Your choice
          </div>
          <ul className="mt-4 space-y-3 text-sm text-slate-600">
            <li>Only you can give or withdraw permission.</li>
            <li>Institution staff can view consent but cannot grant it.</li>
            <li>Reply STOP in WhatsApp or turn updates off here at any time.</li>
          </ul>
        </div>
      </div>

      {!canWithdraw && (
        <form
          className="campus-form mt-5 max-w-2xl"
          onSubmit={(event) => {
            event.preventDefault();
            void submitOptIn(event.currentTarget);
          }}
        >
          <label>
            My WhatsApp number
            <input
              name="phone"
              aria-label="My WhatsApp number"
              type="tel"
              inputMode="tel"
              required
              disabled={!available}
              pattern="^\+[1-9][0-9]{7,14}$"
              title="Use international format without spaces, for example +919876543210"
              defaultValue={status.phone || ""}
              placeholder="+919876543210"
            />
          </label>
          <label className="campus-check">
            <input type="checkbox" required disabled={!available} />
            I agree to receive useful SashaInfinity updates on WhatsApp.
          </label>
          <p className="campus-notice">
            After continuing, send the prepared JOIN message from this number
            to confirm that it belongs to you.
          </p>
          <Button type="submit" loading={busy} disabled={!available}>
            Continue with WhatsApp
          </Button>
        </form>
      )}
    </section>
  );
}

export function CommunicationPreferencesPage() {
  const role = useAuthStore((state) => state.user?.role);
  const administrator = role === "admin" || role === "superadmin";

  return (
    <div className="campus mx-auto max-w-6xl py-2">
      <BrandBanner
        headingLevel="h1"
        eyebrow="SashaInfinity · Communication preferences"
        title="Choose how SashaInfinity reaches you."
        description="Keep important learning and account updates close, with one clear preference for your whole SashaInfinity account."
      >
        {administrator && (
          <Link className="sf-primary" to="/admin/communications">
            Open Communications Center
          </Link>
        )}
      </BrandBanner>

      <div className="grid gap-5 md:grid-cols-2">
        <section className="campus-panel">
          <span className="campus-icon">
            <Bell size={19} />
          </span>
          <h2 className="mt-4 text-lg font-bold text-secondary-900">
            In-app notifications
          </h2>
          <p className="campus-muted mt-2">
            Course activity, learning reminders and campus announcements stay
            available inside SashaInfinity.
          </p>
          <Link
            className="mt-4 inline-flex font-semibold text-orange-700 hover:text-orange-800"
            to="/settings"
          >
            Manage notification topics →
          </Link>
        </section>
        <section className="campus-panel">
          <span className="campus-icon">
            <LockKeyhole size={19} />
          </span>
          <h2 className="mt-4 text-lg font-bold text-secondary-900">
            Permission stays with you
          </h2>
          <p className="campus-muted mt-2">
            Your number is used for messages you approve. Your learning access
            never depends on enabling WhatsApp.
          </p>
        </section>
      </div>

      <WhatsAppPreferenceCard />
    </div>
  );
}

export default CommunicationPreferencesPage;
