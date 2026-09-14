import * as React from "react"
import { cn } from "@/utils/cn"

interface LogoProps {
  className?: string
  size?: "sm" | "md" | "lg" | "xl"
  showText?: boolean
  variant?: "default" | "white" | "dark"
}

export const Logo: React.FC<LogoProps> = ({
  className,
  size = "md",
  }) => {
  const heightClasses = {
    sm: "h-8",
    md: "h-12",
    lg: "h-16",
    xl: "h-20"
  }

  return (
    <div className={cn("flex items-center", className)}>
      <img
        src="https://res.cloudinary.com/dkjvfskhn/image/upload/v1759753621/cropped-sasha-logo-small_ejpceq.png"
        alt="SashaInfinity Logo"
        className={cn("w-auto", heightClasses[size])}
      />
    </div>
  )
}

// Alternative minimalist version
export const LogoMini: React.FC<{ className?: string }> = ({ className }) => {
  return (
    <div className={cn("relative w-10 h-10", className)}>
      <div className="absolute inset-0 bg-gradient-to-br from-primary-500 via-secondary-500 to-accent-500 rounded-lg"></div>
      <div className="absolute inset-[2px] bg-white rounded-[6px] flex items-center justify-center">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          className="w-6 h-6"
        >
          <path
            d="M8.5 12c0-1.5-1.5-3-3-3s-3 1.5-3 3 1.5 3 3 3c1.5 0 3-1.5 3-3zm0 0c0 1.5 1.5 3 3 3s3-1.5 3-3-1.5-3-3-3c-1.5 0-3 1.5-3 3zm7.5 0c0-1.5 1.5-3 3-3s3 1.5 3 3-1.5 3-3 3c-1.5 0-3-1.5-3-3z"
            stroke="url(#miniGradient)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
          <defs>
            <linearGradient id="miniGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#0087ff" />
              <stop offset="50%" stopColor="#00ff88" />
              <stop offset="100%" stopColor="#ff0080" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    </div>
  )
}

// Technology-focused variant with circuit pattern
export const LogoTech: React.FC<{ className?: string; size?: "sm" | "md" | "lg" }> = ({
  className,
  size = "md"
}) => {
  const sizeClasses = {
    sm: "w-8 h-8",
    md: "w-10 h-10",
    lg: "w-12 h-12"
  }

  return (
    <div className={cn("relative", sizeClasses[size], className)}>
      {/* Circuit board background pattern */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary-600 via-primary-500 to-secondary-500 rounded-lg opacity-90"></div>

      {/* Tech grid overlay */}
      <div className="absolute inset-0 opacity-20">
        <svg viewBox="0 0 40 40" className="w-full h-full">
          <defs>
            <pattern id="techGrid" width="8" height="8" patternUnits="userSpaceOnUse">
              <path d="M 8 0 L 0 0 0 8" fill="none" stroke="white" strokeWidth="0.5"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#techGrid)" />
        </svg>
      </div>

      {/* Main infinity symbol */}
      <div className="absolute inset-1 bg-black/5 rounded-md flex items-center justify-center">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          className="w-6 h-6"
        >
          <path
            d="M8.5 12c0-1.5-1.5-3-3-3s-3 1.5-3 3 1.5 3 3 3c1.5 0 3-1.5 3-3zm0 0c0 1.5 1.5 3 3 3s3-1.5 3-3-1.5-3-3-3c-1.5 0-3 1.5-3 3zm7.5 0c0-1.5 1.5-3 3-3s3 1.5 3 3-1.5 3-3 3c-1.5 0-3-1.5-3-3z"
            stroke="white"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
            className="drop-shadow-sm"
          />
        </svg>
      </div>

      {/* Glowing accent */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent rounded-lg"></div>
    </div>
  )
}