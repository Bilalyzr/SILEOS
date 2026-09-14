/**
 * useConfirm — imperative replacement for window.confirm / window.prompt that
 * renders a GlassDialog (2026-09-05 UI pass).
 *
 *   const confirm = useConfirm()
 *   if (await confirm({ title: 'Delete lesson?', body: '…', danger: true })) …
 *   const reason = await confirm.prompt({ title: 'Reason', placeholder: 'optional' })  // string | null
 *
 * Mount <ConfirmProvider> once near the app root.
 */
import * as React from 'react'
import { GlassDialog } from './dialog'

interface ConfirmOptions {
  title: React.ReactNode
  body?: React.ReactNode
  confirmLabel?: string
  cancelLabel?: string
  danger?: boolean
  eyebrow?: React.ReactNode
}
interface PromptOptions extends ConfirmOptions {
  placeholder?: string
  defaultValue?: string
  multiline?: boolean
  required?: boolean
}
type Pending =
  | { kind: 'confirm'; opts: ConfirmOptions; resolve: (v: boolean) => void }
  | { kind: 'prompt'; opts: PromptOptions; resolve: (v: string | null) => void }

interface ConfirmApi {
  (opts: ConfirmOptions): Promise<boolean>
  prompt: (opts: PromptOptions) => Promise<string | null>
}

const Ctx = React.createContext<ConfirmApi | null>(null)

// Module-level registry so plain (non-hook) code can open the same glass
// dialog: `await confirmDialog('Delete this course?')`. Falls back to the
// browser dialogs when no provider is mounted (tests, isolated mounts).
let registry: ConfirmApi | null = null

/** Split a legacy `window.confirm` message into title + body. */
function splitMessage(message: string): { title: string; body?: string } {
  const text = String(message).trim()
  const m = text.match(/^(.{0,90}?[.?!])\s+([\s\S]+)$/)
  if (m) return { title: m[1], body: m[2] }
  return text.length > 100 ? { title: text.slice(0, 97) + '…', body: text } : { title: text }
}

const DANGER_WORDS = /delete|remove|revoke|reject|cancel|reset|ban|suspend|clear|permanent|force/i

export function confirmDialog(message: string, opts: Partial<ConfirmOptions> = {}): Promise<boolean> {
  if (!registry) return Promise.resolve(window.confirm(message))
  const { title, body } = splitMessage(message)
  return registry({ title, body, danger: DANGER_WORDS.test(message), confirmLabel: DANGER_WORDS.test(message) ? 'Yes, do it' : 'OK', ...opts })
}

export function promptDialog(message: string, defaultValue = '', opts: Partial<PromptOptions> = {}): Promise<string | null> {
  if (!registry) return Promise.resolve(window.prompt(message, defaultValue))
  const { title, body } = splitMessage(message)
  return registry.prompt({ title, body, defaultValue, ...opts })
}

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [pending, setPending] = React.useState<Pending | null>(null)
  const [value, setValue] = React.useState('')

  const api = React.useMemo<ConfirmApi>(() => {
    const confirm = ((opts: ConfirmOptions) => new Promise<boolean>((resolve) => setPending({ kind: 'confirm', opts, resolve }))) as ConfirmApi
    confirm.prompt = (opts: PromptOptions) => new Promise<string | null>((resolve) => { setValue(opts.defaultValue || ''); setPending({ kind: 'prompt', opts, resolve }) })
    return confirm
  }, [])
  React.useEffect(() => { registry = api; return () => { if (registry === api) registry = null } }, [api])

  const close = (result: boolean | string | null) => {
    if (!pending) return
    if (pending.kind === 'confirm') pending.resolve(Boolean(result))
    else pending.resolve(typeof result === 'string' ? result : null)
    setPending(null)
  }
  const opts = pending?.opts
  const canSubmit = pending?.kind !== 'prompt' || !(pending.opts.required && !value.trim())

  return (
    <Ctx.Provider value={api}>
      {children}
      <GlassDialog
        open={!!pending}
        onOpenChange={(o) => { if (!o) close(pending?.kind === 'prompt' ? null : false) }}
        size="sm"
        eyebrow={opts?.eyebrow}
        title={opts?.title}
        description={opts?.body}
        data-testid="confirm-dialog"
        actions={pending && (
          <>
            <button type="button" className="si-btn-secondary" onClick={() => close(pending.kind === 'prompt' ? null : false)}>{opts?.cancelLabel || 'Cancel'}</button>
            <button type="button" disabled={!canSubmit} className={opts?.danger ? 'si-btn-danger' : 'si-btn-primary'} onClick={() => close(pending.kind === 'prompt' ? value : true)} autoFocus>
              {opts?.confirmLabel || (pending.kind === 'prompt' ? 'Save' : 'Confirm')}
            </button>
          </>
        )}
      >
        {pending?.kind === 'prompt' && (
          pending.opts.multiline ? (
            <textarea value={value} onChange={(e) => setValue(e.target.value)} rows={3} placeholder={pending.opts.placeholder} className="si-input w-full" autoFocus />
          ) : (
            <input value={value} onChange={(e) => setValue(e.target.value)} placeholder={pending.opts.placeholder} className="si-input w-full" autoFocus
              onKeyDown={(e) => { if (e.key === 'Enter' && canSubmit) close(value) }} />
          )
        )}
      </GlassDialog>
    </Ctx.Provider>
  )
}

export function useConfirm(): ConfirmApi {
  const api = React.useContext(Ctx)
  if (!api) {
    // Fallback keeps callers working outside the provider (tests, isolated mounts).
    const f = ((opts: ConfirmOptions) => Promise.resolve(window.confirm(String(opts.title)))) as ConfirmApi
    f.prompt = (opts: PromptOptions) => Promise.resolve(window.prompt(String(opts.title), opts.defaultValue || ''))
    return f
  }
  return api
}
