import * as React from "react"
import { Star } from "lucide-react"
import { cn } from "@/utils/cn"

interface StarRatingProps {
  rating: number
  maxRating?: number
  size?: "sm" | "md" | "lg"
  readonly?: boolean
  onRatingChange?: (rating: number) => void
  className?: string
  showValue?: boolean
}

const StarRating: React.FC<StarRatingProps> = ({
  rating,
  maxRating = 5,
  size = "md",
  readonly = true,
  onRatingChange,
  className,
  showValue = false,
}) => {
  const [hoverRating, setHoverRating] = React.useState<number | null>(null)

  const sizeClasses = {
    sm: "w-3 h-3",
    md: "w-4 h-4",
    lg: "w-5 h-5"
  }

  const textSizeClasses = {
    sm: "text-xs",
    md: "text-sm",
    lg: "text-base"
  }

  const handleStarClick = (starRating: number) => {
    if (!readonly && onRatingChange) {
      onRatingChange(starRating)
    }
  }

  const handleStarHover = (starRating: number) => {
    if (!readonly) {
      setHoverRating(starRating)
    }
  }

  const handleMouseLeave = () => {
    if (!readonly) {
      setHoverRating(null)
    }
  }

  const displayRating = hoverRating !== null ? hoverRating : rating

  return (
    <div className={cn("flex items-center gap-1", className)}>
      <div
        className="flex items-center gap-0.5"
        onMouseLeave={handleMouseLeave}
      >
        {Array.from({ length: maxRating }, (_, index) => {
          const starRating = index + 1
          const isFilled = starRating <= displayRating
          const isPartiallyFilled =
            starRating > displayRating && starRating - 1 < displayRating

          return (
            <button
              key={index}
              type="button"
              className={cn(
                "focus:outline-none transition-colors duration-200",
                !readonly && "hover:scale-110 cursor-pointer",
                readonly && "cursor-default"
              )}
              onClick={() => handleStarClick(starRating)}
              onMouseEnter={() => handleStarHover(starRating)}
              disabled={readonly}
            >
              <div className="relative">
                <Star
                  className={cn(
                    sizeClasses[size],
                    "text-neutral-300 transition-colors duration-200"
                  )}
                />
                {(isFilled || isPartiallyFilled) && (
                  <Star
                    className={cn(
                      sizeClasses[size],
                      "absolute inset-0 text-yellow-400 fill-current transition-colors duration-200"
                    )}
                    style={{
                      clipPath: isPartiallyFilled
                        ? `inset(0 ${100 - (displayRating - Math.floor(displayRating)) * 100}% 0 0)`
                        : undefined
                    }}
                  />
                )}
              </div>
            </button>
          )
        })}
      </div>

      {showValue && (
        <span className={cn(
          "text-neutral-600 font-medium ml-1",
          textSizeClasses[size]
        )}>
          {rating.toFixed(1)}
        </span>
      )}
    </div>
  )
}

export { StarRating }