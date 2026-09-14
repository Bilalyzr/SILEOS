/**
 * TagsEditor — free-text course tags (v2.0 §3: no taxonomy) with
 * "suggested tags on save": suggestions derived from the course's own title
 * and description via GET /tag-taxonomy/suggest, one click to accept, always
 * dismissible. Existing chips are removable. Debounced so typing a title
 * does not hammer the API.
 */
import * as React from 'react'
import { X, Sparkles } from 'lucide-react'
import { api } from '@/api/axios'

export interface TagsEditorProps {
  tags: string[]
  onChange: (tags: string[]) => void
  title?: string
  description?: string
  className?: string
}

export const TagsEditor: React.FC<TagsEditorProps> = ({ tags, onChange, title = '', description = '', className = '' }) => {
  const [input, setInput] = React.useState('')
  const [suggestions, setSuggestions] = React.useState<string[]>([])
  const [dismissed, setDismissed] = React.useState<Set<string>>(new Set())

  React.useEffect(() => {
    if (!title.trim() && !description.trim()) { setSuggestions([]); return }
    const handle = setTimeout(() => {
      api.get('/tag-taxonomy/suggest', { params: { title: title.slice(0, 300), description: description.slice(0, 5000), existing: tags.join(',') } })
        .then((r) => setSuggestions(r.data?.suggestions || []))
        .catch(() => setSuggestions([]))
    }, 600)
    return () => clearTimeout(handle)
  }, [title, description, tags])

  const add = (raw: string) => {
    const t = raw.trim()
    if (!t || tags.some((x) => x.toLowerCase() === t.toLowerCase())) return
    onChange([...tags, t])
    setInput('')
  }
  const visible = suggestions.filter((s) => !dismissed.has(s) && !tags.some((x) => x.toLowerCase() === s.toLowerCase()))

  return (
    <div className={className}>
      <label className="block text-sm font-medium text-gray-700 mb-2">Tags <span className="text-xs font-normal text-gray-400">(free-form — search unifies spellings automatically)</span></label>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {tags.map((t) => (
          <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-orange-50 border border-orange-200 text-xs text-orange-800">
            {t}
            <button type="button" onClick={() => onChange(tags.filter((x) => x !== t))} aria-label={`Remove tag ${t}`} className="text-orange-400 hover:text-orange-700"><X className="w-3 h-3" /></button>
          </span>
        ))}
        {tags.length === 0 && <span className="text-xs text-gray-400">No tags yet.</span>}
      </div>
      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add(input) } }}
          placeholder="Type a tag and press Enter"
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
        />
        <button type="button" onClick={() => add(input)} className="px-3 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50">Add</button>
      </div>
      {visible.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <span className="inline-flex items-center gap-1 text-[11px] text-gray-500"><Sparkles className="w-3 h-3" /> Suggested from your content:</span>
          {visible.map((s) => (
            <span key={s} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-50 border border-gray-200 text-xs text-gray-700">
              <button type="button" onClick={() => add(s)} className="hover:underline">+ {s}</button>
              <button type="button" onClick={() => setDismissed((d) => new Set(d).add(s))} aria-label={`Dismiss suggestion ${s}`} className="text-gray-400 hover:text-gray-700"><X className="w-3 h-3" /></button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default TagsEditor
