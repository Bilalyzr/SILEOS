import * as React from "react"
import { cn } from "@/utils/cn"

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, label, error, helperText, leftIcon, rightIcon, id, ...props }, ref) => {
    const generatedId = React.useId() // always called; never `id || useId()`
    const inputId = id || generatedId

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-neutral-700 mb-2"
          >
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <span className="text-neutral-500 sm:text-sm">{leftIcon}</span>
            </div>
          )}
          <input
            type={type}
            className={cn(
              "sf-input flex h-10 sm:h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm sm:text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
              leftIcon && "pl-10",
              rightIcon && "pr-10",
              error && "border-danger-500 focus-visible:ring-danger-500",
              className
            )}
            ref={ref}
            id={inputId}
            style={{ fontSize: '16px' }}
            {...props}
          />
          {rightIcon && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              <span className="text-neutral-500 sm:text-sm">{rightIcon}</span>
            </div>
          )}
        </div>
        {error && (
          <p className="mt-2 text-sm text-danger-600">{error}</p>
        )}
        {helperText && !error && (
          <p className="mt-2 text-sm text-neutral-500">{helperText}</p>
        )}
      </div>
    )
  }
)
Input.displayName = "Input"

export { Input }