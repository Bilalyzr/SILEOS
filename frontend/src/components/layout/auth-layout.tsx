import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { AnimatePresence, motion, useMotionValue, useSpring } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { GatewayCanvas } from "@/components/auth/gateway/GatewayCanvas";
import { GatewayContext } from "@/components/auth/gateway/GatewayContext";
import { TrustStrip } from "@/components/auth/gateway/GatewayControls";
import { useCalmMotion } from "@/components/auth/gateway/useCalmMotion";
import { LearningPreferences } from "@/components/labs/LearningPreferences";
import "@/components/auth/gateway/gateway.css";

type Mode = "signin" | "signup";

const STORY: Record<Mode, { eyebrow: string; title: [string, string]; lede: string; legend: string[] }> = {
  signin: {
    eyebrow: "Welcome back · The ∞ path",
    title: ["Your infinite path", "continues here."],
    lede: "Pick up your courses, labs and progress exactly where you left them.",
    legend: ["Learn", "Practice", "Build", "Career"],
  },
  signup: {
    eyebrow: "New here · The Knowledge Triad",
    title: ["Step into the", "Knowledge Triad."],
    lede: "Meiporul, Seyappaduporul and Utporul: courses, hands-on labs and spatial AR in one place.",
    legend: ["Meiporul", "Seyappaduporul", "Utporul"],
  },
};

const HIGHLIGHTS = ["38 spatial AR models", "Browser learning labs", "Verified internships"];

const EASE = [0.2, 0.7, 0.2, 1] as const;

// Panel content turns like a page in the direction of travel
// (custom = +1 toward Create account, -1 back to Sign in).
const sceneVariants = {
  enter: (d: number) => ({ opacity: 0, x: d * 36, rotateY: d * 10, filter: "blur(4px)" }),
  center: { opacity: 1, x: 0, rotateY: 0, filter: "blur(0px)" },
  exit: (d: number) => ({ opacity: 0, x: d * -36, rotateY: d * -10, filter: "blur(4px)" }),
};
const fadeVariants = {
  enter: { opacity: 0 },
  center: { opacity: 1 },
  exit: { opacity: 0 },
};

/** Measures its content so the panel can glide between form heights. */
function AutoHeight({ children }: { children: ReactNode }) {
  const inner = useRef<HTMLDivElement | null>(null);
  const [h, setH] = useState<number | "auto">("auto");
  useEffect(() => {
    const el = inner.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setH(el.offsetHeight));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return (
    <motion.div
      className="ag-autoheight"
      initial={false}
      animate={{ height: h }}
      transition={{ type: "spring", stiffness: 260, damping: 30 }}
    >
      <div ref={inner}>{children}</div>
    </motion.div>
  );
}

/**
 * The authentication gateway: a living knowledge network fills the screen,
 * the story on the left speaks to the current mode, and the form floats on a
 * glass panel. /login and /register share this one instance (same element
 * type at the same place in the route tree), so switching between them morphs
 * the scene rather than loading a new page.
 */
export function AuthLayout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const reduce = useCalmMotion();
  const path = location.pathname.replace(/\/$/, "") || "/";
  const mode: Mode = path === "/register" ? "signup" : "signin";
  const switchable = path === "/login" || path === "/register";
  const story = STORY[mode];

  // Direction of travel for the panel turn
  const prevMode = useRef<Mode>(mode);
  const dir = mode === prevMode.current ? 0 : mode === "signup" ? 1 : -1;
  useEffect(() => {
    prevMode.current = mode;
  }, [mode]);

  // Focus reporting from fields brightens the network
  const focused = useRef(new Set<string>());
  const [focus, setFocus] = useState(0);
  const reportFocus = useCallback((id: string, on: boolean) => {
    if (on) focused.current.add(id);
    else focused.current.delete(id);
    setFocus(focused.current.size > 0 ? 1 : 0);
  }, []);
  const ctx = useMemo(() => ({ reportFocus }), [reportFocus]);

  // Panel leans a little toward the cursor (desktop, motion allowed)
  const rx = useMotionValue(0);
  const ry = useMotionValue(0);
  const rotateX = useSpring(rx, { stiffness: 120, damping: 20 });
  const rotateY = useSpring(ry, { stiffness: 120, damping: 20 });
  const panelRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (reduce || !window.matchMedia("(pointer: fine)").matches) return;
    const onMove = (e: PointerEvent) => {
      const el = panelRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const px = (e.clientX - (r.left + r.width / 2)) / window.innerWidth;
      const py = (e.clientY - (r.top + r.height / 2)) / window.innerHeight;
      ry.set(Math.max(-1, Math.min(1, px)) * 3);
      rx.set(Math.max(-1, Math.min(1, py)) * -2.4);
      el.style.setProperty("--gx", `${e.clientX - r.left}px`);
      el.style.setProperty("--gy", `${e.clientY - r.top}px`);
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, [reduce, rx, ry]);

  return (
    <GatewayContext.Provider value={ctx}>
      <div className={`ag-root ag-mode-${mode}${focus ? " is-focused" : ""}`}>
        <GatewayCanvas mode={mode} focus={focus} />
        <div className="ag-vignette" aria-hidden="true" />

        <header className="ag-topbar">
          <Link to="/" className="ag-brand" aria-label="Sasha Infinity home">
            <motion.span
              className="ag-brand-mark"
              initial={reduce ? false : { scale: 0.6, opacity: 0, filter: "blur(8px)" }}
              animate={{ scale: 1, opacity: 1, filter: "blur(0px)" }}
              transition={{ duration: 0.7, ease: EASE }}
            >
              <img src="/brand/sasha-logo-small.png?v=lion2" alt="" />
            </motion.span>
            <motion.span
              className="ag-brand-word"
              initial={reduce ? false : { opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.25, ease: EASE }}
            >
              <span className="ag-brand-name">
                Sasha<b>Infinity</b>
              </span>
              <small>Knowledge architecture</small>
            </motion.span>
          </Link>
          <div className="ag-topbar-actions">
            {/* The routed page's own accessibility menu sits inside the
                tilting glass panel (a transformed ancestor breaks its
                positioning), so the gateway hosts it up here instead. */}
            <LearningPreferences />
            <Link to="/" className="ag-back">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              <span>Back to site</span>
            </Link>
          </div>
        </header>

        <section className="ag-story">
          <AnimatePresence mode="wait" initial={!reduce}>
            <motion.div
              key={mode}
              initial={reduce ? { opacity: 0 } : { opacity: 0, y: 14, filter: "blur(6px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={reduce ? { opacity: 0 } : { opacity: 0, y: -10, filter: "blur(6px)" }}
              transition={{ duration: 0.5, ease: EASE, delay: dir === 0 ? 0.35 : 0 }}
            >
              <p className="ag-eyebrow">{story.eyebrow}</p>
              <h1 className="ag-title">
                <span>{story.title[0]}</span>
                <span className="ag-title-accent">{story.title[1]}</span>
              </h1>
              <p className="ag-lede">{story.lede}</p>
              <ol className="ag-legend" aria-label={mode === "signin" ? "Learning path" : "Knowledge Triad"}>
                {story.legend.map((item, i) => (
                  <li key={item}>
                    <span className="ag-legend-n">{String(i + 1).padStart(2, "0")}</span>
                    {item}
                  </li>
                ))}
              </ol>
            </motion.div>
          </AnimatePresence>
          <ul className="ag-highlights">
            {HIGHLIGHTS.map((h) => (
              <li key={h}>{h}</li>
            ))}
          </ul>
        </section>

        <main className="ag-stage">
          <motion.div
            ref={panelRef}
            className="ag-panel"
            style={reduce ? undefined : { rotateX, rotateY, transformPerspective: 1400 }}
            initial={reduce ? { opacity: 0 } : { opacity: 0, y: 28, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.2, ease: EASE }}
          >
            <span className="ag-panel-glow" aria-hidden="true" />
            {switchable && (
              <nav className="ag-switch" aria-label="Account access">
                {(["signin", "signup"] as Mode[]).map((m) => (
                  <Link
                    key={m}
                    to={m === "signin" ? "/login" : "/register"}
                    state={location.state}
                    replace
                    className={`ag-switch-tab${mode === m ? " is-active" : ""}`}
                    aria-current={mode === m ? "page" : undefined}
                  >
                    {mode === m && (
                      <motion.span
                        layoutId="ag-switch-pill"
                        className="ag-switch-pill"
                        transition={{ type: "spring", stiffness: 420, damping: 34 }}
                      />
                    )}
                    <span className="ag-switch-label">{m === "signin" ? "Sign in" : "Create account"}</span>
                  </Link>
                ))}
              </nav>
            )}
            <AutoHeight>
              <AnimatePresence mode="wait" initial={false} custom={dir}>
                <motion.div
                  key={path}
                  className="ag-scene"
                  custom={dir}
                  variants={reduce ? fadeVariants : sceneVariants}
                  initial="enter"
                  animate="center"
                  exit="exit"
                  transition={{ duration: 0.34, ease: EASE }}
                >
                  {children}
                </motion.div>
              </AnimatePresence>
            </AutoHeight>
            <TrustStrip />
          </motion.div>
        </main>
      </div>
    </GatewayContext.Provider>
  );
}
