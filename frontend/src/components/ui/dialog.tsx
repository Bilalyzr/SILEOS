/**
 * GlassDialog — the one popup primitive for the platform (2026-09-05 UI pass).
 * Radix Dialog underneath (focus trap, Esc, scroll lock, aria) wrapped in the
 * SashaInfinity glass look: orange-gradient halo, frosted panel, clear title /
 * body / action rows. Use it instead of hand-rolled fixed overlays and
 * window.confirm/prompt — see `useConfirm` in ./confirm.tsx for the imperative
 * version.
 */
import * as React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";

export type GlassDialogSize = "sm" | "md" | "lg" | "xl" | "full";
const SIZES: Record<GlassDialogSize, string> = {
  sm: "max-w-md",
  md: "max-w-xl",
  lg: "max-w-3xl",
  xl: "max-w-5xl",
  full: "max-w-[96vw]",
};

export interface GlassDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: React.ReactNode;
  description?: React.ReactNode;
  /** Small uppercase label above the title (e.g. "Public preview") */
  eyebrow?: React.ReactNode;
  size?: GlassDialogSize;
  /** Dark glass (video / 3D stages) instead of light glass */
  tone?: "light" | "dark";
  children?: React.ReactNode;
  /** Action row rendered at the bottom-right */
  actions?: React.ReactNode;
  hideClose?: boolean;
  className?: string;
  "data-testid"?: string;
}

export function GlassDialog({
  open,
  onOpenChange,
  title,
  description,
  eyebrow,
  size = "md",
  tone = "light",
  children,
  actions,
  hideClose,
  className = "",
  "data-testid": testId,
}: GlassDialogProps) {
  // The shell follows the light Astra system; video/canvas children own their backgrounds.
  const dark = false;
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="astra-scrim fixed inset-0 z-[90] bg-neutral-950/60 backdrop-blur-sm data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <Dialog.Content
          {...(!description ? { "aria-describedby": undefined } : {})}
          data-testid={testId}
          data-media-tone={tone}
          className={`fixed left-1/2 top-1/2 z-[100] w-[calc(100vw-1.5rem)] ${SIZES[size]} -translate-x-1/2 -translate-y-1/2 outline-none`}
        >
          <div className="si-glass-halo">
            <div
              className={`${dark ? "glass-panel-dark text-white" : "glass-panel text-gray-900"} relative rounded-2xl max-h-[92vh] flex flex-col ${className}`}
            >
              {(title || eyebrow || description || !hideClose) && (
                <div
                  className={`flex items-start gap-3 px-5 pt-5 pb-3 ${dark ? "border-b border-white/10" : "border-b border-white/60"}`}
                >
                  <div className="flex-1 min-w-0">
                    {eyebrow && (
                      <p
                        className={`text-[11px] uppercase tracking-wider font-semibold ${dark ? "text-orange-300" : "text-primary-600"}`}
                      >
                        {eyebrow}
                      </p>
                    )}
                    {title ? (
                      <Dialog.Title className="text-lg font-semibold leading-tight">
                        {title}
                      </Dialog.Title>
                    ) : (
                      <Dialog.Title className="sr-only">Dialog</Dialog.Title>
                    )}
                    {description && (
                      <Dialog.Description
                        className={`text-sm mt-0.5 ${dark ? "text-white/70" : "text-gray-600"}`}
                      >
                        {description}
                      </Dialog.Description>
                    )}
                  </div>
                  {!hideClose && (
                    <Dialog.Close asChild>
                      <button
                        type="button"
                        aria-label="Close"
                        className={`h-8 w-8 grid place-items-center rounded-full ${dark ? "hover:bg-white/10 text-white/80" : "hover:bg-black/5 text-gray-600"}`}
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </Dialog.Close>
                  )}
                </div>
              )}
              <div className="px-5 py-4 overflow-y-auto flex-1">{children}</div>
              {actions && (
                <div
                  className={`px-5 py-3 flex flex-wrap justify-end gap-2 ${dark ? "border-t border-white/10" : "border-t border-white/60"}`}
                >
                  {actions}
                </div>
              )}
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** Button styles that match the glass dialogs (also usable anywhere). */
export const glassBtn = {
  primary: "si-btn-primary",
  secondary: "si-btn-secondary",
  danger: "si-btn-danger",
  ghost: "si-btn-ghost",
};

export default GlassDialog;
