import * as React from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import './independence-day.css'

/**
 * 🇮🇳 80th Independence Day flash-offer pop-up (homepage only).
 *
 * Behaviour:
 *  - Appears AT LEAST ONCE per browser session — drops in ~1.2s after the
 *    first homepage visit of the session (flagged via sessionStorage) and
 *    auto-closes after 10s (close button / backdrop / Escape close it
 *    sooner). Reloads within the same session don't repeat it; the static
 *    corner timer (OfferTimerWidget) keeps the offer visible instead.
 *  - Live countdown chip pinned to the bottom-right of the card until the
 *    deadline (Sunday 16 Aug 2026, 12:00 PM IST, expressed in UTC so it
 *    is correct in any timezone). At 00:00:00:00 the timer — and the
 *    whole popup — remove themselves; after the deadline it never renders.
 *  - Crackers + sparkles are pure CSS around the card border — no
 *    canvas / rAF loop — and respect `prefers-reduced-motion`.
 */

// Sun, 16 Aug 2026 12:00:00 PM IST == 06:30:00 UTC
const OFFER_DEADLINE_UTC = Date.parse('2026-08-16T06:30:00Z')
const SHOW_DELAY_MS = 1200
const AUTO_CLOSE_MS = 10000

// "at least once per session" flag — sessionStorage so a fresh visit
// (new tab session / next day) sees the pop-up again.
const SHOWN_KEY = 'sasha-offer-popup-shown'

// Firework palette — Indian flag tricolor ONLY.
const SAFFRON = '#FF9933'
const WHITE = '#FFFFFF'
const GREEN = '#138808'
const CRACKER_COLORS = [SAFFRON, WHITE, GREEN]

// Shared with the corner timer widget (OfferTimerWidget) so both always
// count down to the exact same deadline.
export interface TimeLeft {
  days: number
  hours: number
  minutes: number
  seconds: number
}

export function getTimeLeft(): TimeLeft | null {
  const remaining = OFFER_DEADLINE_UTC - Date.now()
  if (remaining <= 0) return null
  const totalSeconds = Math.floor(remaining / 1000)
  return {
    days: Math.floor(totalSeconds / 86400),
    hours: Math.floor((totalSeconds % 86400) / 3600),
    minutes: Math.floor((totalSeconds % 3600) / 60),
    seconds: totalSeconds % 60,
  }
}

/* ---------------- firework pieces ---------------- */

interface CrackerParticle {
  dx: number
  dy: number
  color: string
  delay: number
  size: number
}

/** Deterministic set of particles thrown outward from one burst origin. */
function makeCracker(count: number, radius: number): CrackerParticle[] {
  return Array.from({ length: count }, (_, i) => {
    const angle = (i / count) * Math.PI * 2 + 0.4
    const r = radius * (0.7 + (((i * 37) % 10) / 10) * 0.55)
    return {
      dx: Math.round(Math.cos(angle) * r),
      dy: Math.round(Math.sin(angle) * r),
      color: CRACKER_COLORS[i % CRACKER_COLORS.length],
      delay: (((i * 53) % 10) / 10) * 0.14,
      size: 4 + ((i * 29) % 3),
    }
  })
}

interface CrackerProps {
  count?: number
  radius?: number
  /** loop length in seconds — long enough that bursts feel "occasional" */
  period: number
  /** loop offset in seconds, staggers the clusters */
  delay: number
  /** tint of the origin flash */
  color: string
  /** anchor point on the card border */
  style?: React.CSSProperties
}

const Cracker: React.FC<CrackerProps> = ({ count = 10, radius = 42, period, delay, color, style }) => (
  <span
    className="idp-cracker"
    style={
      {
        ...style,
        '--t': `${period}s`,
        '--flash': color,
      } as React.CSSProperties
    }
  >
    {makeCracker(count, radius).map((p, i) => (
      <i
        key={i}
        style={
          {
            width: p.size,
            height: p.size,
            background: p.color,
            boxShadow: `0 0 8px 1px ${p.color}`,
            '--dx': `${p.dx}px`,
            '--dy': `${p.dy}px`,
            animationDelay: `${delay + p.delay}s`,
          } as React.CSSProperties
        }
      />
    ))}
  </span>
)

// Small twinkling dots pinned to the tricolor border. White ones sit just
// outside the card so they glow against the dimmed backdrop.
const SPARKLES: React.CSSProperties[] = [
  { top: '-5px', left: '20%', width: 5, height: 5, background: SAFFRON, boxShadow: `0 0 7px 1px ${SAFFRON}`, animationDelay: '0.3s' },
  { top: '-5px', left: '64%', width: 4, height: 4, background: GREEN, boxShadow: `0 0 7px 1px ${GREEN}`, animationDelay: '1.1s' },
  { top: '32%', left: '-6px', width: 5, height: 5, background: WHITE, boxShadow: `0 0 8px 1px rgba(255,255,255,0.9)`, animationDelay: '0.7s' },
  { top: '66%', left: '-6px', width: 4, height: 4, background: SAFFRON, boxShadow: `0 0 7px 1px ${SAFFRON}`, animationDelay: '1.9s' },
  { top: '26%', right: '-6px', width: 5, height: 5, background: GREEN, boxShadow: `0 0 7px 1px ${GREEN}`, animationDelay: '1.5s' },
  { top: '70%', right: '-6px', width: 4, height: 4, background: WHITE, boxShadow: `0 0 8px 1px rgba(255,255,255,0.9)`, animationDelay: '0.9s' },
  { bottom: '-5px', left: '32%', width: 5, height: 5, background: SAFFRON, boxShadow: `0 0 7px 1px ${SAFFRON}`, animationDelay: '2.3s' },
  { bottom: '-5px', left: '76%', width: 4, height: 4, background: GREEN, boxShadow: `0 0 7px 1px ${GREEN}`, animationDelay: '0.5s' },
]

/* ---------------- countdown ---------------- */

const pad = (n: number) => String(n).padStart(2, '0')

/** Compact live countdown chip — pinned to the card's bottom-right. */
const Countdown: React.FC<{ left: TimeLeft }> = ({ left }) => {
  const segments = [
    { value: pad(left.days), label: 'Days' },
    { value: pad(left.hours), label: 'Hours' },
    { value: pad(left.minutes), label: 'Minutes' },
    { value: pad(left.seconds), label: 'Seconds' },
  ]

  return (
    <div className="idp-timer" role="timer" aria-label="Time left in offer">
      {segments.map((seg, i) => (
        <React.Fragment key={seg.label}>
          {i > 0 && <span className="idp-t-colon">:</span>}
          <span className="idp-t-seg">
            {/* keyed by value so the number replays its pop when it changes */}
            <span key={seg.value} className="idp-t-num">
              {seg.value}
            </span>
            <span className="idp-t-label">{seg.label}</span>
          </span>
        </React.Fragment>
      ))}
    </div>
  )
}

/* ---------------- the pop-up ---------------- */

export const IndependenceDayPopup: React.FC = () => {
  const [open, setOpen] = React.useState(false)
  const [left, setLeft] = React.useState<TimeLeft | null>(() => getTimeLeft())

  const close = React.useCallback(() => {
    setOpen(false)
  }, [])

  // Show at least once per browser session until the offer expires.
  // The flag is set only when the pop-up actually OPENS (not during effect
  // setup) so React StrictMode's dev double-invocation can't consume the
  // one show by cancelling the first timer.
  React.useEffect(() => {
    if (!getTimeLeft()) return
    try {
      if (window.sessionStorage.getItem(SHOWN_KEY) === '1') return
    } catch {
      /* storage unavailable (private mode) — still show it */
    }
    const timer = window.setTimeout(() => {
      try {
        window.sessionStorage.setItem(SHOWN_KEY, '1')
      } catch {
        /* ignore — worst case it shows again next load */
      }
      setLeft(getTimeLeft())
      setOpen(true)
    }, SHOW_DELAY_MS)
    return () => window.clearTimeout(timer)
  }, [])

  // While open: 1s countdown tick, auto-close, scroll lock, Escape.
  React.useEffect(() => {
    if (!open) return

    const tick = window.setInterval(() => {
      const remaining = getTimeLeft()
      if (!remaining) {
        close()
        return
      }
      setLeft(remaining)
    }, 1000)

    const autoClose = window.setTimeout(close, AUTO_CLOSE_MS)
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', onKeyDown)

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      window.clearInterval(tick)
      window.clearTimeout(autoClose)
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [open, close])

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          className="idp-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
          onClick={close}
        >
          <motion.div
            className="idp-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="idp-title"
            initial={{ scale: 0.82, y: 26, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.92, y: 14, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 24 }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Fireworks — tricolor crackers + sparkles around the border */}
            <div className="idp-fireworks" aria-hidden="true">
              <Cracker period={3.8} delay={0.15} color={SAFFRON} style={{ top: '12%', left: '-4px' }} />
              <Cracker period={4.6} delay={1.9} color={GREEN} style={{ bottom: '16%', right: '-4px' }} radius={48} />
              <Cracker period={4.2} delay={3.1} color={WHITE} style={{ top: '40%', right: '-5px' }} radius={34} count={8} />
              {SPARKLES.map((style, i) => (
                <span key={i} className="idp-sparkle" style={style} />
              ))}
            </div>

            <div className="idp-card-inner">
              <button type="button" className="idp-close" onClick={close} aria-label="Close offer" autoFocus>
                ✕
              </button>

              <div className="idp-eyebrow">
                <span className="idp-flag" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                </span>
                80th Independence Day Special
              </div>

              <h2 className="idp-title" id="idp-title">
                <span className="idp-off">50% OFF</span>
                on ALL Courses!
              </h2>

              <p className="idp-lead">
                Celebrate the <strong>80th Independence Day</strong> with us!
                <br />
                Get <strong>50% OFF</strong> on all our courses — <strong>today only!</strong>
              </p>

              <div className="idp-badge">Limited-Time Independence Day Offer</div>

              <Link to="/courses" className="idp-cta" onClick={close}>
                🚀 EXPLORE NOW
              </Link>

              {/* Footer: deadline note bottom-left, live timer bottom-right.
                  When the countdown hits zero the tick effect closes the
                  popup, so `left` going null never lingers on screen. */}
              <div className="idp-footer">
                <span className="idp-deadline">
                  ⏰ Offer ends Sunday, 16 Aug · 12:00 PM IST
                </span>
                {left && <Countdown left={left} />}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  )
}
