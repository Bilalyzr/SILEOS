import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/utils/cn";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary-100 text-primary-800",
        secondary: "border-transparent bg-secondary-100 text-secondary-800",
        success: "border-transparent bg-success-100 text-success-800",
        warning: "border-transparent bg-warning-100 text-warning-800",
        danger: "border-transparent bg-danger-100 text-danger-800",
        outline: "border-primary-200 text-primary-700",
        neutral: "border-transparent bg-neutral-100 text-neutral-800",
      },
      size: {
        default: "px-2.5 py-0.5 text-xs",
        sm: "px-2 py-0.5 text-xs",
        lg: "px-3 py-1 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, size, ...props }: BadgeProps) {
  return (
    <div
      data-status={variant || "default"}
      className={cn("astra-badge", badgeVariants({ variant, size }), className)}
      {...props}
    />
  );
}

export { Badge, badgeVariants };
