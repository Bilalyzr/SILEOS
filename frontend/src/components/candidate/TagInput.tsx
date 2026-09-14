import * as React from 'react'
import { X } from 'lucide-react'

interface TagInputProps {
  value: string[]
  onChange: (next: string[]) => void
  placeholder?: string
  suggestions?: string[]
  maxTags?: number
}

export const TagInput: React.FC<TagInputProps> = ({
  value,
  onChange,
  placeholder = 'Type and press Enter',
  suggestions = [],
  maxTags = 20,
}) => {
  const [draft, setDraft] = React.useState('')

  const addTag = (raw: string) => {
    const t = raw.trim()
    if (!t) return
    if (value.includes(t)) return
    if (value.length >= maxTags) return
    onChange([...value, t])
    setDraft('')
  }

  const removeTag = (i: number) => {
    onChange(value.filter((_, idx) => idx !== i))
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addTag(draft)
    } else if (e.key === 'Backspace' && !draft && value.length > 0) {
      removeTag(value.length - 1)
    }
  }

  return (
    <div>
      <div className="flex flex-wrap gap-2 rounded-md border border-neutral-300 bg-white p-2 min-h-[48px] focus-within:border-primary-500">
        {value.map((tag, i) => (
          <span
            key={`${tag}-${i}`}
            className="inline-flex items-center gap-1 rounded-full bg-primary-100 px-3 py-1.5 text-sm text-primary-800"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(i)}
              className="text-primary-600 hover:text-primary-900 p-1 min-h-[32px] min-w-[32px] flex items-center justify-center"
              aria-label={`Remove ${tag}`}
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={() => addTag(draft)}
          placeholder={value.length === 0 ? placeholder : ''}
          className="flex-1 min-w-[120px] outline-none text-base bg-transparent py-2"
          style={{ fontSize: '16px' }}
        />
      </div>
      {suggestions.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {suggestions
            .filter((s) => !value.includes(s))
            .slice(0, 8)
            .map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => addTag(s)}
                className="rounded-full border border-neutral-300 px-3 py-1.5 text-xs text-neutral-600 hover:border-primary-500 hover:text-primary-700 min-h-[36px] transition-colors"
              >
                + {s}
              </button>
            ))}
        </div>
      )}
    </div>
  )
}

export default TagInput
