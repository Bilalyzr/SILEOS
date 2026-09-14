/**
 * "Share on LinkedIn" dialog for an earned certificate.
 *
 * Replaces the old behaviour where LinkedIn received only the website link and
 * rendered a generic site preview. Here the student gets:
 *   - the actual certificate image as the post preview (via the backend's
 *     Open-Graph share page — see utils/certificate-share.ts for why),
 *   - a personalised caption they can edit before posting,
 *   - the official SashaInfinity page referenced in the caption,
 *   - the standard SashaInfinity hashtag set.
 */
import * as React from 'react'
import { createPortal } from 'react-dom'
import { Linkedin, Copy, Check, X, ExternalLink, Loader2, Info } from 'lucide-react'
import toast from 'react-hot-toast'
import { certificatesAPI, CertificateShareMeta } from '@/api/certificates'
import {
  buildCertificateCaption,
  buildLinkedInComposerUrl,
  buildLinkedInShareOffsiteUrl,
  copyToClipboard,
  SASHA_LINKEDIN_PAGE,
  SASHA_LINKEDIN_HANDLE,
} from '@/utils/certificate-share'

const hostnameOf = (url: string): string => {
  try {
    return new URL(url).hostname
  } catch {
    return 'sashainfinity.com'
  }
}

export interface LinkedInShareDialogProps {
  open: boolean
  onClose: () => void
  secureCertificateId: string
  certificateHash: string
  /** Used for the offline fallback caption if share-meta can't be fetched. */
  courseTitle?: string
}

export const LinkedInShareDialog: React.FC<LinkedInShareDialogProps> = ({
  open,
  onClose,
  secureCertificateId,
  certificateHash,
  courseTitle = 'my course',
}) => {
  const [meta, setMeta] = React.useState<CertificateShareMeta | null>(null)
  const [caption, setCaption] = React.useState('')
  const [isLoading, setIsLoading] = React.useState(true)
  const [copied, setCopied] = React.useState(false)
  const [imageFailed, setImageFailed] = React.useState(false)

  // Fallback used when the backend payload can't be fetched — the share URL is
  // deterministic, so a useful post is still possible offline.
  const fallbackShareUrl = React.useMemo(
    () =>
      `${window.location.origin}/api/v1/certificates/share/${secureCertificateId}/${certificateHash}`,
    [secureCertificateId, certificateHash]
  )

  React.useEffect(() => {
    if (!open) return
    let cancelled = false

    const load = async () => {
      setIsLoading(true)
      setImageFailed(false)
      try {
        const data = await certificatesAPI.getShareMeta(secureCertificateId, certificateHash)
        if (cancelled) return
        setMeta(data)
        setCaption(data.caption)
      } catch {
        if (cancelled) return
        setMeta(null)
        setCaption(buildCertificateCaption({ courseTitle, shareUrl: fallbackShareUrl }))
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [open, secureCertificateId, certificateHash, courseTitle, fallbackShareUrl])

  // Escape to close + lock background scroll while the dialog is up.
  React.useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [open, onClose])

  if (!open) return null

  const shareUrl = meta?.share_url || fallbackShareUrl
  const imageUrl =
    meta?.image_url ||
    `${window.location.origin}/api/v1/certificates/image/${secureCertificateId}/${certificateHash}.png`
  const companyPage = meta?.company_page || SASHA_LINKEDIN_PAGE
  const companyHandle = meta?.company_handle || SASHA_LINKEDIN_HANDLE

  const handleCopyCaption = async () => {
    const ok = await copyToClipboard(caption)
    if (ok) {
      setCopied(true)
      toast.success('Caption copied')
      setTimeout(() => setCopied(false), 2000)
    } else {
      toast.error('Could not copy — select the caption and copy manually')
    }
    return ok
  }

  const handleShare = async () => {
    // Copy first: the composer deep-link pre-fills the caption, but some
    // LinkedIn surfaces strip it — having it on the clipboard means the
    // student can always paste it back.
    await copyToClipboard(caption)
    window.open(buildLinkedInComposerUrl(caption), '_blank', 'noopener,noreferrer')
    toast.success('Caption copied — finish your post on LinkedIn')
  }

  const handleShareLinkOnly = () => {
    window.open(buildLinkedInShareOffsiteUrl(shareUrl), '_blank', 'noopener,noreferrer')
  }

  return createPortal(
    <div
      className="fixed inset-0 z-modal flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Share certificate on LinkedIn"
    >
      <div
        className="bg-white w-full max-w-3xl max-h-[92vh] overflow-y-auto rounded-2xl shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 px-6 py-4 border-b border-slate-200 sticky top-0 bg-white rounded-t-2xl z-10">
          <div className="flex items-center gap-3 min-w-0">
            <span className="w-10 h-10 rounded-xl bg-[#0A66C2]/10 text-[#0A66C2] flex items-center justify-center flex-shrink-0">
              <Linkedin className="w-5 h-5" />
            </span>
            <div className="min-w-0">
              <h2 className="font-semibold text-slate-900">Share on LinkedIn</h2>
              <p className="text-xs text-slate-500 truncate">
                Your certificate is used as the post preview image
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="p-2 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 flex-shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center gap-3 py-20 text-slate-500">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="text-sm">Preparing your certificate preview…</span>
          </div>
        ) : (
          <div className="p-6 space-y-5">
            {/* Preview card — mirrors how the LinkedIn post will look. */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
                Post preview
              </p>
              <div className="rounded-xl border border-slate-200 overflow-hidden bg-slate-50">
                {imageFailed ? (
                  <div className="h-48 flex flex-col items-center justify-center text-center px-6 text-slate-500">
                    <p className="text-sm font-medium text-slate-700">Preview image still rendering</p>
                    <p className="text-xs mt-1">
                      LinkedIn will pick it up once it finishes. You can still share now.
                    </p>
                  </div>
                ) : (
                  <img
                    src={imageUrl}
                    alt="Your certificate"
                    className="w-full h-auto block bg-white"
                    onError={() => setImageFailed(true)}
                  />
                )}
                <div className="px-4 py-3 bg-white border-t border-slate-200">
                  <p className="text-[11px] uppercase tracking-wide text-slate-400">
                    {hostnameOf(shareUrl)}
                  </p>
                  <p className="text-sm font-semibold text-slate-900 truncate">
                    {meta?.og_title || 'Certificate of Completion — SashaInfinity'}
                  </p>
                  <p className="text-xs text-slate-500 line-clamp-2">
                    {meta?.og_description || 'Verified certificate of completion.'}
                  </p>
                </div>
              </div>
            </div>

            {/* Caption */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Your caption
                </p>
                <button
                  onClick={handleCopyCaption}
                  className="text-xs font-semibold text-orange-600 hover:text-orange-700 flex items-center gap-1"
                >
                  {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? 'Copied' : 'Copy caption'}
                </button>
              </div>
              <textarea
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                rows={12}
                className="w-full rounded-xl border border-slate-200 p-4 text-sm text-slate-800 leading-relaxed focus:outline-none focus:ring-2 focus:ring-orange-400/40 focus:border-orange-400 resize-y"
                spellCheck={false}
              />
            </div>

            {/* Mention hint — LinkedIn cannot pre-fill a real page mention from
                a share link, so the caption carries the handle as text. */}
            <div className="flex gap-3 rounded-xl bg-sky-50 border border-sky-100 p-3.5">
              <Info className="w-4 h-4 text-sky-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-sky-900 leading-relaxed">
                To tag our page properly, retype <strong>{companyHandle}</strong> in the LinkedIn
                composer and pick <strong>SashaInfinity</strong> from the dropdown — LinkedIn only
                creates a real mention when it's selected there.{' '}
                <a
                  href={companyPage}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold underline underline-offset-2"
                >
                  Open our page
                </a>
              </p>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 pt-1">
              <button
                onClick={handleShare}
                className="flex-1 inline-flex items-center justify-center gap-2 bg-[#0A66C2] hover:bg-[#084d92] text-white font-semibold rounded-xl px-5 py-3 transition"
              >
                <Linkedin className="w-4 h-4" />
                Share on LinkedIn
              </button>
              <button
                onClick={handleShareLinkOnly}
                className="inline-flex items-center justify-center gap-2 border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold rounded-xl px-5 py-3 transition"
                title="Share the certificate link without a caption"
              >
                <ExternalLink className="w-4 h-4" />
                Link only
              </button>
            </div>

            <p className="text-[11px] text-slate-400 text-center">
              Anyone with this link can view and verify your certificate.
            </p>
          </div>
        )}
      </div>
    </div>,
    document.body
  )
}

export default LinkedInShareDialog
