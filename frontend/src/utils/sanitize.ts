import DOMPurify from 'dompurify'

/**
 * Sanitize untrusted HTML before rendering it via `dangerouslySetInnerHTML`.
 *
 * Blog/course/lesson/quiz/assignment bodies are authored by instructors and
 * bloggers and rendered to other users, so raw HTML is a stored-XSS vector.
 * Run every such string through this before injecting it.
 */
export const sanitizeHtml = (html: string): string =>
  DOMPurify.sanitize(html || '', { USE_PROFILES: { html: true } })
