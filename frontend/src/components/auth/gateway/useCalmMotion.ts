import { useReducedMotion } from "framer-motion";

/**
 * True when motion should be calm: the OS "reduce motion" setting, or the
 * site's own Reduce motion switch in the accessibility menu (which sets
 * body[data-reduce-motion="true"]).
 */
export function prefersCalmMotion(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
    document.body?.dataset.reduceMotion === "true"
  );
}

export function useCalmMotion(): boolean {
  const os = useReducedMotion();
  return Boolean(os) || (typeof document !== "undefined" && document.body?.dataset.reduceMotion === "true");
}
