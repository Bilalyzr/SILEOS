/**
 * Mobile number helpers.
 *
 * Mirrors `normalize_mobile_number` in backend/app/routers/auth.py: an optional
 * +91 / 0091 / 91 / 0 prefix is stripped and the rest must be a 10-digit Indian
 * mobile number. Validating client-side keeps the mandatory-number prompts from
 * round-tripping to the API just to be told the format is wrong.
 */

export function normalizeMobileNumber(raw: string): string {
  const digits = (raw || '').replace(/\D/g, '')

  if (digits.length === 12 && digits.startsWith('91')) return digits.slice(2)
  if (digits.length === 13 && digits.startsWith('0091')) return digits.slice(4)
  if (digits.length === 11 && digits.startsWith('0')) return digits.slice(1)

  return digits
}

export function isValidMobileNumber(raw: string): boolean {
  return /^[6-9]\d{9}$/.test(normalizeMobileNumber(raw))
}

export const MOBILE_NUMBER_ERROR = 'Enter a valid 10-digit mobile number'
