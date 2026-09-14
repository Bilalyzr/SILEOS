import * as React from "react"
import * as ProgressPrimitive from "@radix-ui/react-progress"
import { cn } from "@/utils/cn"

const Progress = React.forwardRef<
  React.ElementRef<typeof ProgressPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root> & {
    showLabel?: boolean
    label?: string
    size?: "sm" | "md" | "lg"
    variant?: "default" | "success" | "warning" | "danger"
  }
>(({ className, value = 0, showLabel = false, label, size = "md", variant = "default", ...props }, ref) => {
  const sizeClasses = {
    sm: "h-1",
    md: "h-2",
    lg: "h-3"
  }

  const variantClasses = {
    default: "bg-primary-500",
    success: "bg-success-500",
    warning: "bg-warning-500",
    danger: "bg-danger-500"
  }

  return (
    <div className="w-full">
      {(showLabel || label) && (
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm font-medium text-neutral-700">
            {label || "Progress"}
          </span>
          <span className="text-sm text-neutral-500">{Math.round(value || 0)}%</span>
        </div>
      )}
      <ProgressPrimitive.Root
        ref={ref}
        className={cn(
          "relative overflow-hidden rounded-full bg-neutral-200",
          sizeClasses[size],
          className
        )}
        {...props}
      >
        <ProgressPrimitive.Indicator
          className={cn(
            "h-full w-full flex-1 transition-all duration-300 ease-in-out",
            variantClasses[variant]
          )}
          style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
        />
      </ProgressPrimitive.Root>
    </div>
  )
})
Progress.displayName = ProgressPrimitive.Root.displayName

export { Progress }