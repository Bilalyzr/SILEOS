import * as React from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { getTimeLeft, type TimeLeft } from './IndependenceDayPopup'
import './offer-timer.css'

/**
 * 🇮🇳 Independence Day offer — static bottom-right corner timer section.
 *
 * Always-present companion to <IndependenceDayPopup /> (mounted on the
 * Home and Courses pages): it pins the offer content (50% OFF all
 * courses) and the live countdown to the bottom-right corner for as long
 * as the offer runs (see the shared deadline in IndependenceDayPopup).
 *
 *  - Static by design: shown immediately on mount, no dismiss button —
 *    it stays until the offer ends.
 *  - Renders null forever once the deadline passes (at 00:00:00:00 it
 *    removes itself).
 *  - Sits above the homepage scroll-top button and dims behind the
 *    pop-up overlay while that is open.
 */

const pad = (n: number) => String(n).padStart(2, '0')

/** Compact countdown chip for the corner card. */
const Countdown: React.FC<{ left: TimeLeft }> = ({ left }) => {
  const segments = [
    { value: pad(left.days), label: 'Days' },
    { value: pad(left.hours), label: 'Hours' },
    { value: pad(left.minutes), label: 'Mins' },
    { value: pad(left.seconds), label: 'Secs' },
  ]

  return (
    <div className="otw-timer" role="timer" aria-label="Time left in offer">
      {segments.map((seg, i) => (
        <React.Fragment key={seg.label}>
          {i > 0 && <span className="otw-t-colon">:</span>}
          <span className="otw-t-seg">
            {/* keyed by value so the number replays its pop when it changes */}
            <span key={seg.value} className="otw-t-num">
              {seg.value}
            </span>
            <span className="otw-t-label">{seg.label}</span>
          </span>
        </React.Fragment>
      ))}
    </div>
  )
}

export const OfferTimerWidget: React.FC = () => {
  const [left, setLeft] = React.useState<TimeLeft | null>(() => getTimeLeft())

  // 1s countdown tick from mount; at zero the offer is over — leave.
  React.useEffect(() => {
    if (!getTimeLeft()) return
    const tick = window.setInterval(() => setLeft(getTimeLeft()), 1000)
    return () => window.clearInterval(tick)
  }, [])

  return createPortal(
    <AnimatePresence>
      {left && (
        <motion.aside
          className="otw-card"
          aria-label="Independence Day offer — time remaining"
          initial={{ x: 48, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 48, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 280, damping: 26 }}
        >
          <div className="otw-inner">
            <div className="otw-eyebrow">
              <span className="otw-flag" aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
              80th Independence Day Special
            </div>

            <h3 className="otw-title">
              <span className="otw-off">50% OFF</span>
              on ALL Courses!
            </h3>

            <Countdown left={left} />

            <span className="otw-deadline">⏰ Offer ends Sunday, 16 Aug · 12:00 PM IST</span>

            <Link to="/courses" className="otw-cta">
              🚀 EXPLORE NOW
            </Link>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>,
    document.body
  )
}
