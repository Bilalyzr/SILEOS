import React, { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Horizontally scrollable table wrapper with a second scrollbar pinned above
 * the table.
 *
 * Wide admin tables only expose a scrollbar under the last row, so on a long
 * list you have to scroll to the bottom of the page before you can pan
 * sideways. This renders a mirror scrollbar on top and keeps the two in sync.
 * The top bar hides itself when the content fits, so narrow tables are
 * unaffected.
 */
export const TableScrollArea: React.FC<{
  children: React.ReactNode
  className?: string
}> = ({ children, className = '' }) => {
  const topRef = useRef<HTMLDivElement>(null)
  const bodyRef = useRef<HTMLDivElement>(null)
  // Guards against the sync handlers echoing each other back and forth.
  const syncing = useRef(false)
  const [contentWidth, setContentWidth] = useState(0)
  const [overflows, setOverflows] = useState(false)

  const measure = useCallback(() => {
    const body = bodyRef.current
    if (!body) return
    setContentWidth(body.scrollWidth)
    setOverflows(body.scrollWidth > body.clientWidth + 1)
  }, [])

  useEffect(() => {
    const body = bodyRef.current
    if (!body) return

    measure()

    // Rows load asynchronously and columns reflow on resize — re-measure on both.
    const observer = new ResizeObserver(measure)
    observer.observe(body)
    if (body.firstElementChild) observer.observe(body.firstElementChild)

    window.addEventListener('resize', measure)
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', measure)
    }
    // Deliberately not keyed on `children`: that changes identity every render
    // and would tear down and rebuild the observers each time. The
    // ResizeObserver already catches rows arriving or columns reflowing.
  }, [measure])

  const sync = (from: HTMLDivElement | null, to: HTMLDivElement | null) => {
    if (!from || !to || syncing.current) return
    syncing.current = true
    to.scrollLeft = from.scrollLeft
    // Release on the next frame; assigning scrollLeft fires the peer's onScroll.
    requestAnimationFrame(() => {
      syncing.current = false
    })
  }

  return (
    <div className={className}>
      <div
        ref={topRef}
        onScroll={() => sync(topRef.current, bodyRef.current)}
        className="overflow-x-auto overflow-y-hidden border-b border-gray-100 bg-gray-50"
        // Collapsed to nothing when the table fits, so narrow tables look
        // exactly as they did before.
        style={{ height: overflows ? 14 : 0 }}
        aria-hidden="true"
      >
        <div style={{ width: contentWidth, height: 1 }} />
      </div>

      <div
        ref={bodyRef}
        onScroll={() => sync(bodyRef.current, topRef.current)}
        className="overflow-x-auto"
      >
        {children}
      </div>
    </div>
  )
}
