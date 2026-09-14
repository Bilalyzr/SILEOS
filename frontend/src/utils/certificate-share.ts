/**
 * Certificate → LinkedIn sharing helpers.
 *
 * Why this exists: LinkedIn's `share-offsite` endpoint shares a *URL only* —
 * it builds the preview card from that URL's Open Graph tags and carries no
 * post text. So a good certificate share needs two things working together:
 *
 *   1. A share URL whose og:image is the rendered certificate. That is the
 *      backend's `/api/v1/certificates/share/{id}/{hash}` landing page — it is
 *      what makes the certificate itself show up as the post preview instead
 *      of the generic SashaInfinity logo.
 *   2. A caption pre-filled into the LinkedIn composer, which only the
 *      `/feed/?shareActive=true&text=` composer deep-link supports.
 *
 * The caption text below mirrors `_build_share_payload` in
 * `backend/app/routers/certificates.py`. The backend copy is authoritative
 * (the dialog fetches it); this one is the offline fallback for when the
 * share-meta request fails.
 */

export const SASHA_LINKEDIN_PAGE = 'https://www.linkedin.com/company/sashainfinity/'
export const SASHA_LINKEDIN_HANDLE = '@SashaInfinity'

export const CERTIFICATE_HASHTAGS = [
  'SashaInfinity',
  'Certification',
  'ContinuousLearning',
  'ProfessionalDevelopment',
  'Upskilling',
  'CareerGrowth',
  'LifelongLearning',
]

/** "AI For Everyone" → "AIForEveryone". Returns null when nothing usable survives. */
export function courseHashtag(courseTitle: string): string | null {
  const words = courseTitle
    .replace(/[^a-zA-Z0-9]+/g, ' ')
    .split(' ')
    .filter(Boolean)
  const tag = words.map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join('')
  if (!tag || !/^[a-zA-Z]/.test(tag) || tag.length > 40) return null
  return tag
}

export interface CaptionInput {
  courseTitle: string
  shareUrl: string
}

/** Personalised post caption — kept in sync with the backend builder. */
export function buildCertificateCaption({ courseTitle, shareUrl }: CaptionInput): string {
  const hashtags = [...CERTIFICATE_HASHTAGS]
  const courseTag = courseHashtag(courseTitle)
  if (courseTag && !hashtags.includes(courseTag)) hashtags.splice(1, 0, courseTag)

  return [
    `🎉 Proud to have successfully completed "${courseTitle}" at SashaInfinity!`,
    '',
    'Grateful for the opportunity to learn, grow, and enhance my skills. ' +
      'Looking forward to applying this knowledge in real-world projects.',
    '',
    `Thank you, SashaInfinity (${SASHA_LINKEDIN_HANDLE}), for this learning experience!`,
    '',
    `🔗 Verify my certificate: ${shareUrl}`,
    '',
    hashtags.map((t) => `#${t}`).join(' '),
  ].join('\n')
}

/**
 * LinkedIn composer deep-link. Opens the "start a post" box with the caption
 * already typed in; the share URL inside the caption is what LinkedIn unfurls
 * into the certificate preview card.
 */
export function buildLinkedInComposerUrl(caption: string): string {
  return `https://www.linkedin.com/feed/?shareActive=true&text=${encodeURIComponent(caption)}`
}

/**
 * Plain URL share. No caption support — used only as the fallback when the
 * composer deep-link is unavailable (e.g. some in-app browsers).
 */
export function buildLinkedInShareOffsiteUrl(shareUrl: string): string {
  return `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`
}

/** Best-effort clipboard write that also works on non-secure origins. */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch {
    // fall through to the legacy path
  }

  try {
    const el = document.createElement('textarea')
    el.value = text
    el.setAttribute('readonly', '')
    el.style.position = 'fixed'
    el.style.opacity = '0'
    document.body.appendChild(el)
    el.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(el)
    return ok
  } catch {
    return false
  }
}
