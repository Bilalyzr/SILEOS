import * as React from "react";
import { AnimatePresence, motion, useAnimationControls } from "framer-motion";
import { Check, Info } from "lucide-react";
import { useGateway } from "./GatewayContext";
import { useCalmMotion } from "./useCalmMotion";

export interface GatewayFieldProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> {
  id: string;
  label: string;
  icon?: React.ReactNode;
  /** Guidance shown under the field when something needs fixing. */
  error?: string;
  /** Quiet helper text when there is no error. */
  hint?: React.ReactNode;
  /** Shows a check once the value is known to be good. */
  valid?: boolean;
  /** Extra control inside the field, right side (e.g. the eye toggle). */
  trailing?: React.ReactNode;
  /** Rendered under the field, above the error (e.g. a strength meter). */
  below?: React.ReactNode;
}

/**
 * Floating-label input: the label rests inside the field and lifts on focus
 * or once filled (CSS :placeholder-shown, so it works with uncontrolled
 * react-hook-form fields). A gradient border sweeps around on focus, a soft
 * light follows the cursor, and errors arrive as calm amber guidance with a
 * small nudge instead of a red alarm.
 */
export const GatewayField = React.forwardRef<HTMLInputElement, GatewayFieldProps>(
  (
    { id, label, icon, error, hint, valid, trailing, below, className, onFocus, onBlur, disabled, ...rest },
    ref
  ) => {
    const { reportFocus } = useGateway();
    const reduce = useCalmMotion();
    const wrapRef = React.useRef<HTMLDivElement | null>(null);
    const msgId = `${id}-msg`;
    const hasMsg = Boolean(error || hint);
    const nudge = useAnimationControls();

    // A small nudge whenever new guidance appears (never on reduced motion)
    React.useEffect(() => {
      if (error && !reduce) void nudge.start({ x: [0, -5, 5, -2, 0], transition: { duration: 0.36 } });
    }, [error, reduce, nudge]);

    const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
      const el = wrapRef.current;
      if (!el || e.pointerType !== "mouse") return;
      const r = el.getBoundingClientRect();
      el.style.setProperty("--mx", `${e.clientX - r.left}px`);
      el.style.setProperty("--my", `${e.clientY - r.top}px`);
    };

    return (
      <div className="ag-field-block">
        <motion.div
          ref={wrapRef}
          onPointerMove={onPointerMove}
          className={`ag-field${error ? " is-error" : ""}${valid && !error ? " is-valid" : ""}${
            disabled ? " is-disabled" : ""
          }${icon ? " has-icon" : ""}`}
          animate={nudge}
        >
          {icon && (
            <span className="ag-field-icon" aria-hidden="true">
              {icon}
            </span>
          )}
          <input
            ref={ref}
            id={id}
            placeholder=" "
            disabled={disabled}
            aria-invalid={error ? true : undefined}
            aria-describedby={hasMsg ? msgId : undefined}
            className={`ag-input${className ? ` ${className}` : ""}`}
            onFocus={(e) => {
              reportFocus(id, true);
              onFocus?.(e);
            }}
            onBlur={(e) => {
              reportFocus(id, false);
              onBlur?.(e);
            }}
            {...rest}
          />
          <label htmlFor={id} className="ag-label">
            {label}
          </label>
          <span className="ag-field-end">
            <AnimatePresence>
              {valid && !error && (
                <motion.span
                  key="ok"
                  className="ag-field-ok"
                  initial={{ scale: 0.4, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.4, opacity: 0 }}
                  transition={{ type: "spring", stiffness: 420, damping: 22 }}
                  aria-hidden="true"
                >
                  <Check className="h-3.5 w-3.5" strokeWidth={3} />
                </motion.span>
              )}
            </AnimatePresence>
            {trailing}
          </span>
        </motion.div>
        {below}
        <AnimatePresence initial={false}>
          {hasMsg && (
            <motion.p
              key={error ? `e-${error}` : "hint"}
              id={msgId}
              className={`ag-field-msg${error ? " is-error" : ""}`}
              role={error ? "alert" : undefined}
              initial={{ opacity: 0, height: 0, y: -4 }}
              animate={{ opacity: 1, height: "auto", y: 0 }}
              exit={{ opacity: 0, height: 0, y: -4 }}
              transition={{ duration: 0.22, ease: [0.2, 0.7, 0.3, 1] }}
            >
              {error && <Info className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />}
              <span>{error || hint}</span>
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    );
  }
);
GatewayField.displayName = "GatewayField";
