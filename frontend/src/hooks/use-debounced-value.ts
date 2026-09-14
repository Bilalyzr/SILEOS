import { useEffect, useState } from 'react'

/**
 * Returns `value` delayed by `delay` ms. Used by the monitoring tables so a
 * search box fires one request after typing stops instead of one per keystroke.
 */
export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])

  return debounced
}
