import type { HTMLAttributes } from "react";
import { cn } from "@/utils/cn";

/** Ambient is for labels; content is for reading; work is for actionable data. */
export function GlassSurface({
  tier = "content",
  className,
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  tier?: "ambient" | "content" | "work";
}) {
  return (
    <div
      data-glass={tier}
      className={cn("astra-surface", className)}
      {...props}
    />
  );
}
