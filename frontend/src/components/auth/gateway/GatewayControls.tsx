import * as React from "react";
import { AnimatePresence, motion, useMotionValue, useSpring } from "framer-motion";

import { GatewayField, type GatewayFieldProps } from "./GatewayField";
import { useCalmMotion } from "./useCalmMotion";

/* ── Password ─────────────────────────────────────────────────────────── */

export function passwordStrength(value: string) {
  if (!value) return { score: 0, label: "" };
  let score = 0;
  if (value.length >= 8) score++;
  if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score++;
  if (/\d/.test(value)) score++;
  if (/[^A-Za-z0-9]/.test(value) || value.length >= 14) score++;
  if (value.length < 8) score = Math.min(score, 1);
  const labels = ["Too short", "Getting there", "Fair", "Strong", "Excellent"];
  return { score, label: labels[score] };
}

function EyeToggle({ shown }: { shown: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z" />
      <motion.circle cx="12" cy="12" r="3" initial={false} animate={{ scale: shown ? 1 : 0.6, opacity: shown ? 1 : 0.55 }} />
      {/* Slash draws across when the password is hidden */}
      <motion.path d="M4 4l16 16" initial={false} animate={{ pathLength: shown ? 0 : 1, opacity: shown ? 0 : 1 }} transition={{ duration: 0.28 }} />
    </svg>
  );
}

type PasswordFieldProps = Omit<GatewayFieldProps, "type" | "trailing" | "below"> & {
  /** Show the strength meter (sign up). */
  meter?: boolean;
};

/**
 * Password input with an animated show/hide eye, a Caps Lock heads-up and,
 * for new passwords, a four-step strength meter that fills as rules are met.
 */
export const PasswordField = React.forwardRef<HTMLInputElement, PasswordFieldProps>(
  ({ meter, onChange, onKeyUp, hint, ...props }, ref) => {
    const [shown, setShown] = React.useState(false);
    const [caps, setCaps] = React.useState(false);
    const [value, setValue] = React.useState("");
    const strength = passwordStrength(value);

    return (
      <GatewayField
        {...props}
        ref={ref}
        type={shown ? "text" : "password"}
        onChange={(e) => {
          setValue(e.target.value);
          onChange?.(e);
        }}
        onKeyUp={(e) => {
          setCaps(e.getModifierState?.("CapsLock") ?? false);
          onKeyUp?.(e);
        }}
        hint={caps ? "Caps Lock is on." : hint}
        trailing={
          <button
            type="button"
            className="ag-eye"
            onClick={() => setShown((s) => !s)}
            disabled={props.disabled}
            aria-label={shown ? "Hide password" : "Show password"}
            aria-pressed={shown}
          >
            <EyeToggle shown={shown} />
          </button>
        }
        below={
          meter ? (
            <div className="ag-meter" data-score={strength.score} aria-live="polite">
              <div className="ag-meter-bars" aria-hidden="true">
                {[1, 2, 3, 4].map((i) => (
                  <span key={i} className={i <= strength.score ? "on" : ""} />
                ))}
              </div>
              <span className="ag-meter-label">
                {value ? `Strength: ${strength.label}` : "Use 8+ characters with a mix of letters, numbers and symbols"}
              </span>
            </div>
          ) : undefined
        }
      />
    );
  }
);
PasswordField.displayName = "PasswordField";

/* ── Primary action ───────────────────────────────────────────────────── */

function InfinitySpinner() {
  return (
    <svg viewBox="-24 -12 48 24" className="ag-spin" aria-hidden="true">
      <path d="M0 0C6-8 18-8 18 0S6 8 0 0-18-8-18 0-6 8 0 0" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" pathLength={100} />
    </svg>
  );
}

/**
 * Main submit button: leans toward the cursor (magnetic), a light sweep
 * crosses it on hover, and while busy it shows a tracing ∞ instead of a
 * generic spinner.
 */
export function MagneticButton({
  children,
  loading,
  loadingLabel,
  className,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { loading?: boolean; loadingLabel?: string }) {
  const reduce = useCalmMotion();
  const ref = React.useRef<HTMLButtonElement | null>(null);
  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const x = useSpring(mx, { stiffness: 260, damping: 18 });
  const y = useSpring(my, { stiffness: 260, damping: 18 });

  const onMove = (e: React.PointerEvent<HTMLButtonElement>) => {
    const el = ref.current;
    if (!el || reduce || e.pointerType !== "mouse") return;
    const r = el.getBoundingClientRect();
    mx.set(((e.clientX - r.left) / r.width - 0.5) * 10);
    my.set(((e.clientY - r.top) / r.height - 0.5) * 6);
    el.style.setProperty("--bx", `${e.clientX - r.left}px`);
  };
  const reset = () => {
    mx.set(0);
    my.set(0);
  };

  return (
    <motion.button
      ref={ref}
      style={{ x, y }}
      onPointerMove={onMove}
      onPointerLeave={reset}
      whileTap={reduce ? undefined : { scale: 0.98 }}
      className={`ag-primary${loading ? " is-loading" : ""}${className ? ` ${className}` : ""}`}
      aria-busy={loading || undefined}
      {...(rest as any)}
    >
      <span className="ag-primary-sheen" aria-hidden="true" />
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={loading ? "busy" : "idle"}
          className="ag-primary-label"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.16 }}
        >
          {loading ? (
            <>
              <InfinitySpinner />
              {loadingLabel || "Working…"}
            </>
          ) : (
            children
          )}
        </motion.span>
      </AnimatePresence>
    </motion.button>
  );
}

/* ── Third-party providers ────────────────────────────────────────────── */

export const GoogleMark = () => (
  <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09Z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z" />
    <path fill="#FBBC05" d="M5.84 14.09a6.6 6.6 0 0 1 0-4.18V7.07H2.18a11 11 0 0 0 0 9.86l3.66-2.84Z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15A11 11 0 0 0 2.18 7.07l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38Z" />
  </svg>
);

export const LinkedInMark = () => (
  <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
    <rect width="24" height="24" rx="4" fill="#0A66C2" />
    <path fill="#fff" d="M7.1 9.6h2.3V17H7.1V9.6Zm1.15-3.7a1.33 1.33 0 1 1 0 2.66 1.33 1.33 0 0 1 0-2.66ZM10.8 9.6h2.2v1h.03c.31-.58 1.06-1.2 2.18-1.2 2.33 0 2.76 1.53 2.76 3.53V17h-2.3v-3.6c0-.86-.02-1.96-1.2-1.96-1.2 0-1.38.94-1.38 1.9V17h-2.3V9.6Z" />
  </svg>
);

/**
 * Provider tile: lifts toward the cursor with a highlight that enters from
 * the side the pointer came from.
 */
export function ProviderCard({
  mark,
  name,
  note,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { mark: React.ReactNode; name: string; note: string }) {
  const onMove = (e: React.PointerEvent<HTMLButtonElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty("--px", `${e.clientX - r.left}px`);
    e.currentTarget.style.setProperty("--py", `${e.clientY - r.top}px`);
  };
  return (
    <button type="button" className="ag-provider" onPointerMove={onMove} {...rest}>
      <span className="ag-provider-mark">{mark}</span>
      <span className="ag-provider-text">
        <span className="ag-provider-name">Continue with {name}</span>
        <span className="ag-provider-note">{note}</span>
      </span>
    </button>
  );
}

/* ── Trust ────────────────────────────────────────────────────────────── */

/**
 * Quiet security strip: a lock that clicks shut as the panel settles, the
 * connection state, and what the platform does (and does not do) with data.
 */
export function TrustStrip() {
  const secure = typeof window !== "undefined" && window.location.protocol === "https:";
  return (
    <div className="ag-trust" role="note" aria-label="Security">
      <span className="ag-trust-lock" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round">
          <motion.path
            d="M8 11V8a4 4 0 0 1 8 0v3"
            initial={{ y: -3 }}
            animate={{ y: 0 }}
            transition={{ delay: 1.1, type: "spring", stiffness: 500, damping: 18 }}
          />
          <rect x="5" y="11" width="14" height="10" rx="2.5" />
          <circle cx="12" cy="16" r="1.2" fill="currentColor" />
        </svg>
      </span>
      <span className="ag-trust-items">
        <span>
          <i className={`ag-dot${secure ? "" : " is-local"}`} aria-hidden="true" />
          {secure ? "Encrypted connection" : "Local connection"}
        </span>
        <span>Two-factor ready</span>
        <a href="/privacy">We don&apos;t sell your data</a>
      </span>
    </div>
  );
}

