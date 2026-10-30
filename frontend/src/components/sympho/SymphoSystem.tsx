import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link, useInRouterContext } from "react-router-dom";

let sharedRevealObserver: IntersectionObserver | null = null;

function isReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

function getRevealObserver(): IntersectionObserver | null {
  if (typeof window === "undefined" || typeof IntersectionObserver === "undefined") {
    return null;
  }
  if (!sharedRevealObserver) {
    sharedRevealObserver = new IntersectionObserver(
      (entries) => {
        const vh = window.innerHeight || 800;
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.setAttribute("data-revealed", "");
          } else if (entry.boundingClientRect.top > vh * 0.92) {
            // Reset when scrolled back above the element so scrolling down replays the animation
            entry.target.removeAttribute("data-revealed");
          }
        }
      },
      { rootMargin: "0px 0px -6% 0px", threshold: [0, 0.08, 0.2] }
    );
  }
  return sharedRevealObserver;
}

export function observeSymphoReveal(
  el: Element | null,
  opts?: {
    mode?: "fade" | "mask" | "split" | "draw" | "icon";
    delay?: number;
  }
): () => void {
  if (!el) return () => {};
  const mode = opts?.mode ?? "fade";
  if (mode === "split") {
    el.setAttribute("data-split", "");
  } else if (mode === "draw") {
    el.setAttribute("data-draw", "");
  } else if (mode === "icon") {
    el.classList.add("icon-draw");
  } else {
    el.setAttribute("data-reveal", mode === "mask" ? "mask" : "");
  }

  if (opts?.delay && el instanceof HTMLElement) {
    el.style.setProperty("--reveal-delay", `${opts.delay}ms`);
  }

  const obs = getRevealObserver();
  if (!obs || isReducedMotion()) {
    el.setAttribute("data-revealed", "");
    return () => {};
  }
  obs.observe(el);
  return () => {
    obs.unobserve(el);
  };
}

/**
 * Automatically observes elements with [data-reveal], [data-split], [data-draw], .icon-draw,
 * plus architectural cards (.sheet-frame, article, list items) inside a page container,
 * AND drives inertial smooth scrolling + top scroll progress bar + scroll-linked parallax.
 */
export function useSymphoAutoReveal(rootRef: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const root = rootRef.current;
    if (!root || typeof window === "undefined") return;

    const scanAndObserve = () => {
      const obs = getRevealObserver();
      // 1. Explicitly tagged reveal elements
      const explicitNodes = root.querySelectorAll(
        "[data-reveal], [data-split], [data-draw], .icon-draw"
      );
      explicitNodes.forEach((node) => {
        if (!obs || isReducedMotion()) {
          node.setAttribute("data-revealed", "");
        } else {
          obs.observe(node);
        }
      });

      // 2. Architectural cards, articles, grid items, and FAQ rows not already inside a reveal wrapper
      const autoCandidates = root.querySelectorAll(
        "section article, section .sheet-frame, section details, section dl > div, section .container-page > ol > li, section .container-page > ul > li, footer .container-page > div"
      );
      autoCandidates.forEach((node, idx) => {
        if (
          node.hasAttribute("data-reveal") ||
          node.hasAttribute("data-no-auto-reveal") ||
          node.closest("#process")
        ) {
          return;
        }
        node.setAttribute("data-reveal", "");
        if (node instanceof HTMLElement && !node.style.getPropertyValue("--reveal-delay")) {
          const siblingIndex = idx % 4;
          if (siblingIndex > 0) {
            node.style.setProperty("--reveal-delay", `${siblingIndex * 65}ms`);
          }
        }
        if (!obs || isReducedMotion()) {
          node.setAttribute("data-revealed", "");
        } else {
          obs.observe(node);
        }
      });
    };

    scanAndObserve();

    let mo: MutationObserver | undefined;
    if (typeof MutationObserver !== "undefined") {
      mo = new MutationObserver(() => {
        scanAndObserve();
      });
      mo.observe(root, { childList: true, subtree: true });
    }

    // 3. Passive Scroll Progress Bar & Smooth Anchor Link Scrolling (never blocks native wheel/touch scroll)
    let progRaf = 0;

    const updateProgress = () => {
      progRaf = 0;
      const docHeight = Math.max(
        1,
        document.documentElement.scrollHeight - window.innerHeight
      );
      const progress = Math.min(1, Math.max(0, window.scrollY / docHeight));
      root.style.setProperty("--scroll-progress", progress.toFixed(4));
    };

    const onScroll = () => {
      if (!progRaf) {
        progRaf = requestAnimationFrame(updateProgress);
      }
    };

    const onAnchorClick = (e: MouseEvent) => {
      const target = (e.target as HTMLElement | null)?.closest?.("a[href^='#']") as HTMLAnchorElement | null;
      if (!target) return;
      const hash = target.getAttribute("href");
      if (!hash || hash === "#") return;
      const dest = document.querySelector(hash);
      if (!dest) return;
      e.preventDefault();
      dest.scrollIntoView({ behavior: "smooth", block: "start" });
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    root.addEventListener("click", onAnchorClick);
    updateProgress();

    return () => {
      mo?.disconnect();
      cancelAnimationFrame(progRaf);
      window.removeEventListener("scroll", onScroll);
      root.removeEventListener("click", onAnchorClick);
    };
  }, [rootRef]);
}

export interface SymphoCountUpProps {
  value: number;
  decimals?: number;
  className?: string;
}

export const SymphoCountUp: React.FC<SymphoCountUpProps> = ({
  value,
  decimals = 0,
  className,
}) => {
  const spanRef = useRef<HTMLSpanElement | null>(null);
  const formatNum = useCallback(
    (v: number) =>
      new Intl.NumberFormat("en-IN", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }).format(v),
    [decimals]
  );

  const [display, setDisplay] = useState(() => formatNum(value));

  useEffect(() => {
    const el = spanRef.current;
    if (
      !el ||
      typeof IntersectionObserver === "undefined" ||
      isReducedMotion()
    ) {
      setDisplay(formatNum(value));
      return;
    }

    let raf = 0;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        io.disconnect();
        const start = performance.now();
        const tick = (now: number) => {
          const t = Math.min(1, (now - start) / 1800);
          const eased = 1 - (1 - t) ** 4;
          setDisplay(formatNum(value * eased));
          if (t < 1) {
            raf = requestAnimationFrame(tick);
          }
        };
        raf = requestAnimationFrame(tick);
      },
      { threshold: 0.5 }
    );
    io.observe(el);

    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [value, formatNum]);

  return (
    <span ref={spanRef} className={className}>
      {display}
    </span>
  );
};

export interface SplitHeadingProps {
  as?: "h1" | "h2" | "h3" | "h4";
  text: string;
  className?: string;
  italicLast?: number;
  id?: string;
  delay?: number;
}

export const SplitHeading: React.FC<SplitHeadingProps> = ({
  as: Tag = "h2",
  text,
  className = "",
  italicLast = 2,
  id,
  delay,
}) => {
  const ref = useRef<HTMLHeadingElement | null>(null);

  useEffect(() => {
    return observeSymphoReveal(ref.current, { mode: "split", delay });
  }, [delay, text]);

  const words = text.trim().split(/\s+/);
  return (
    <Tag
      ref={ref as any}
      id={id}
      data-split=""
      className={`font-display font-medium ${
        italicLast === 2 ? "split-last-two" : ""
      } ${className}`}
    >
      {words.map((word, idx) => {
        const isAccent = italicLast > 0 && idx >= words.length - italicLast;
        return (
          <React.Fragment key={`${word}-${idx}`}>
            <span
              className={`split-word ${
                isAccent
                  ? "not-italic text-copper-500 [.on-dark_&]:text-copper-300"
                  : ""
              }`}
              style={{ ["--i" as string]: idx }}
            >
              <span>{word}</span>
            </span>
            {idx < words.length - 1 ? " " : ""}
          </React.Fragment>
        );
      })}
    </Tag>
  );
};

export interface SymphoButtonProps {
  children: React.ReactNode;
  to?: string;
  href?: string;
  onClick?: React.MouseEventHandler<HTMLButtonElement | HTMLAnchorElement>;
  variant?:
    | "primary"
    | "on-dark"
    | "outline"
    | "outline-dark"
    | "ghost-dark"
    | "copper";
  size?: "sm" | "md" | "lg";
  arrow?: boolean;
  type?: "button" | "submit" | "reset";
  disabled?: boolean;
  className?: string;
  ariaLabel?: string;
  testId?: string;
}

export const SymphoButton: React.FC<SymphoButtonProps> = ({
  children,
  to,
  href,
  onClick,
  variant = "primary",
  size = "md",
  arrow = false,
  type = "button",
  disabled = false,
  className = "",
  ariaLabel,
  testId,
}) => {
  const ref = useRef<HTMLElement | null>(null);

  const handlePointerMove = useCallback((e: React.PointerEvent<HTMLElement>) => {
    const el = ref.current;
    if (!el || isReducedMotion()) return;
    const rect = el.getBoundingClientRect();
    const dx = (e.clientX - (rect.left + rect.width / 2)) * 0.22;
    const dy = (e.clientY - (rect.top + rect.height / 2)) * 0.22;
    el.style.transition = "transform 120ms linear";
    el.style.transform = `translate3d(${dx.toFixed(1)}px, ${dy.toFixed(1)}px, 0)`;
  }, []);

  const handlePointerLeave = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    el.style.transition = "transform 600ms var(--ease-spring)";
    el.style.transform = "";
  }, []);

  const sizeClasses =
    size === "sm"
      ? "px-4 py-2 text-xs min-h-[2.35rem] gap-2"
      : size === "lg"
      ? "px-7 py-4 text-base min-h-[3.35rem] gap-3"
      : "px-5 py-3 text-sm min-h-[2.85rem] gap-2.5";

  const variantClasses =
    variant === "on-dark"
      ? "bg-copper-500 text-white font-bold hover:text-limestone-50 [--fill:#9a390b] border border-[#c2410c] shadow-[0_7px_20px_rgba(194,65,12,0.25),inset_0_1px_0_#ffffff]"
      : variant === "outline-dark" || variant === "ghost-dark"
      ? "bg-transparent text-limestone-50 border border-limestone-100/35 hover:border-[#c2410c] hover:text-white [--fill:#c2410c]"
      : variant === "outline"
      ? "bg-white text-[#9a3412] border border-[#e4e7ec] hover:border-[#9a390b] hover:text-limestone-50 [--fill:#9a390b]"
      : variant === "copper"
      ? "bg-copper-500 text-white font-bold hover:text-limestone-50 [--fill:#9a390b] border border-[#c2410c] shadow-[0_7px_20px_rgba(194,65,12,0.25),inset_0_1px_0_#ffffff]"
      : "bg-copper-500 text-white font-bold hover:text-limestone-50 [--fill:#9a390b] border border-[#c2410c] shadow-[0_7px_20px_rgba(194,65,12,0.25),inset_0_1px_0_#ffffff]";

  const inner = (
    <>
      <span aria-hidden="true" className="sympho-btn-fill" />
      <span
        data-magnetic-inner=""
        className="relative z-10 inline-flex items-center gap-2.5"
      >
        <span>{children}</span>
        {arrow && (
          <span
            aria-hidden="true"
            className="relative inline-grid size-4 place-items-center overflow-hidden"
          >
            <svg
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              className="size-3.5 sympho-btn-arrow-1"
            >
              <path
                d="M4 12L12 4M6 4h6v6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <svg
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              className="size-3.5 sympho-btn-arrow-2"
            >
              <path
                d="M4 12L12 4M6 4h6v6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
        )}
      </span>
    </>
  );

  const combinedClass = `sympho-btn group/btn ${sizeClasses} ${variantClasses} ${
    disabled ? "opacity-60 pointer-events-none" : ""
  } ${className}`;

  const inRouter = useInRouterContext();

  if (to && inRouter) {
    return (
      <Link
        ref={(node) => {
          ref.current = node;
        }}
        to={to}
        onClick={onClick as any}
        onPointerMove={handlePointerMove}
        onPointerLeave={handlePointerLeave}
        aria-label={ariaLabel}
        data-testid={testId}
        className={combinedClass}
      >
        {inner}
      </Link>
    );
  }

  if (href || to) {
    return (
      <a
        ref={(node) => {
          ref.current = node;
        }}
        href={href || to}
        onClick={onClick as any}
        onPointerMove={handlePointerMove}
        onPointerLeave={handlePointerLeave}
        aria-label={ariaLabel}
        data-testid={testId}
        className={combinedClass}
      >
        {inner}
      </a>
    );
  }

  return (
    <button
      ref={(node) => {
        ref.current = node;
      }}
      type={type}
      disabled={disabled}
      onClick={onClick as any}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      aria-label={ariaLabel}
      data-testid={testId}
      className={combinedClass}
    >
      {inner}
    </button>
  );
};

export interface SymphoSectionHeaderProps {
  index?: string;
  eyebrow?: string;
  category?: string;
  code?: string;
  title: string;
  lede?: string;
  subtitle?: string;
  action?: React.ReactNode;
  align?: "split" | "left";
  headingId?: string;
  dark?: boolean;
}

export const SymphoSectionHeader: React.FC<SymphoSectionHeaderProps> = ({
  index,
  eyebrow,
  category,
  code,
  title,
  lede,
  subtitle,
  action,
  align = "split",
  headingId,
}) => {
  const eyebrowRef = useRef<HTMLDivElement | null>(null);
  const ledeRef = useRef<HTMLParagraphElement | null>(null);
  const actionRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const clean1 = observeSymphoReveal(eyebrowRef.current, { mode: "fade" });
    const clean2 = observeSymphoReveal(ledeRef.current, {
      mode: "fade",
      delay: 140,
    });
    const clean3 = observeSymphoReveal(actionRef.current, {
      mode: "fade",
      delay: 220,
    });
    return () => {
      clean1();
      clean2();
      clean3();
    };
  }, []);

  const resolvedEyebrow = eyebrow || category || "";
  const resolvedLede = lede || subtitle;
  return (
    <header
      className={`grid grid-cols-1 gap-6 ${
        align === "split"
          ? "lg:grid-cols-12 lg:items-end lg:gap-10"
          : "max-w-3xl"
      }`}
    >
      <div className={align === "split" ? "lg:col-span-7" : ""}>
        <div
          ref={eyebrowRef}
          data-reveal=""
          className="mb-5 flex flex-wrap items-center gap-4"
        >
          {index && (
            <span className="font-mono text-label text-copper-500 [.on-dark_&]:text-copper-300">
              {index}
            </span>
          )}
          {resolvedEyebrow && (
            <span className="sheet-label">{resolvedEyebrow}</span>
          )}
          {code && (
            <span className="font-mono text-label opacity-65">· {code}</span>
          )}
        </div>
        <SplitHeading
          as="h2"
          id={headingId}
          text={title}
          className="text-display-lg tracking-tight"
          italicLast={2}
        />
      </div>
      {(resolvedLede || action) && (
        <div
          className={`${
            align === "split" ? "lg:col-span-5 lg:pl-6" : ""
          } flex flex-col justify-end gap-6`}
        >
          {resolvedLede && (
            <p
              ref={ledeRef}
              data-reveal=""
              className="text-lede text-ink-600 [.on-dark_&]:text-limestone-300"
            >
              {resolvedLede}
            </p>
          )}
          {action && (
            <div ref={actionRef} data-reveal="">
              {action}
            </div>
          )}
        </div>
      )}
    </header>
  );
};

export const SymphoDimensionLine: React.FC<{ className?: string }> = ({
  className = "mt-6 h-3 w-full text-ink-900/35",
}) => {
  const svgRef = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    return observeSymphoReveal(svgRef.current, { mode: "draw" });
  }, []);

  return (
    <svg
      ref={svgRef}
      data-draw=""
      aria-hidden="true"
      preserveAspectRatio="none"
      viewBox="0 0 100 12"
      className={className}
      fill="none"
    >
      <path
        d="M0.5 0V12M99.5 0V12M0 6H100"
        stroke="currentColor"
        vectorEffect="non-scaling-stroke"
        pathLength={1}
        className="draw-path"
        fill="none"
      />
    </svg>
  );
};

// The ∞ learning pathway (lemniscate of Bernoulli, the same curve as the
// opening loader and InfinityTrace), scaled into the 800×500 sheet.
const BLUEPRINT_PATH =
  "M649.9 250.0 L648.3 266.2 L643.6 281.8 L636.1 296.1 L626.2 308.6 L614.5 318.9 L601.4 327.1 L587.5 332.9 L573.1 336.6 L558.8 338.2 L544.7 338.1 L531.0 336.3 L517.8 333.3 L505.3 329.1 L493.4 324.1 L482.1 318.3 L471.4 311.8 L461.3 304.9 L451.6 297.7 L442.4 290.1 L433.5 282.3 L424.8 274.4 L416.4 266.3 L408.2 258.2 L400.0 250.0 L391.8 241.8 L383.6 233.7 L375.2 225.6 L366.5 217.7 L357.6 209.9 L348.4 202.3 L338.7 195.1 L328.6 188.2 L317.9 181.7 L306.6 175.9 L294.7 170.9 L282.2 166.7 L269.0 163.7 L255.3 161.9 L241.2 161.8 L226.9 163.4 L212.5 167.1 L198.6 172.9 L185.5 181.1 L173.8 191.4 L163.9 203.9 L156.4 218.2 L151.7 233.8 L150.1 250.0 L151.7 266.2 L156.4 281.8 L163.9 296.1 L173.8 308.6 L185.5 318.9 L198.6 327.1 L212.5 332.9 L226.9 336.6 L241.2 338.2 L255.3 338.1 L269.0 336.3 L282.2 333.3 L294.7 329.1 L306.6 324.1 L317.9 318.3 L328.6 311.8 L338.7 304.9 L348.4 297.7 L357.6 290.1 L366.5 282.3 L375.2 274.4 L383.6 266.3 L391.8 258.2 L400.0 250.0 L408.2 241.8 L416.4 233.7 L424.8 225.6 L433.5 217.7 L442.4 209.9 L451.6 202.3 L461.3 195.1 L471.4 188.2 L482.1 181.7 L493.4 175.9 L505.3 170.9 L517.8 166.7 L531.0 163.7 L544.7 161.9 L558.8 161.8 L573.1 163.4 L587.5 167.1 L601.4 172.9 L614.5 181.1 L626.2 191.4 L636.1 203.9 L643.6 218.2 L648.3 233.8Z";

/**
 * Page-hero watermark: a knowledge-architecture drawing of the site's own
 * concept. The ∞ pathway carries the Learn → Practice → Build → Career
 * milestones; the Tamil Knowledge Triad (Meiporul · Seyappaduporul ·
 * Utporul) orbits it as a triangle, with a Meiporul solid at its apex. A
 * point of light travels the path (hidden under reduced motion).
 */
export const SymphoBlueprintSvg: React.FC<{ className?: string }> = ({
  className = "h-full w-full text-limestone-100",
}) => (
  <svg
    viewBox="0 0 800 500"
    fill="none"
    stroke="currentColor"
    strokeWidth="1"
    className={className}
  >
    <style>
      {"@media (prefers-reduced-motion: reduce){.si-bp-comet{display:none}}"}
    </style>
    {/* Drafting grid and centre lines */}
    <g opacity="0.18" strokeDasharray="3 5">
      <line x1="40" y1="250" x2="760" y2="250" />
      <line x1="400" y1="20" x2="400" y2="480" />
      <line x1="150" y1="120" x2="150" y2="380" />
      <line x1="650" y1="120" x2="650" y2="380" />
    </g>

    {/* Triad orbit and triangle */}
    <ellipse
      cx="400"
      cy="250"
      rx="340"
      ry="215"
      strokeDasharray="6 5"
      opacity="0.4"
    />
    <path
      d="M400 35 L106 357 L694 357 Z"
      strokeDasharray="2 6"
      opacity="0.35"
    />

    {/* Inner rings framing the pathway */}
    <ellipse cx="400" cy="250" rx="275" ry="118" opacity="0.28" />
    <ellipse
      cx="400"
      cy="250"
      rx="210"
      ry="150"
      transform="rotate(-14 400 250)"
      opacity="0.22"
    />

    {/* The ∞ learning pathway */}
    <path d={BLUEPRINT_PATH} strokeWidth="1.8" />
    <path
      d={BLUEPRINT_PATH}
      strokeWidth="7"
      opacity="0.08"
      strokeLinejoin="round"
    />

    {/* Dimension line across the pathway */}
    <g opacity="0.55">
      <path d="M150 412 H650 M150 404 V420 M650 404 V420" />
      <path d="M150 412 l8 -4 v8 Z M650 412 l-8 -4 v8 Z" fill="currentColor" />
    </g>

    {/* Meiporul solid at the triad apex (isometric cube) */}
    <g strokeWidth="1.2">
      <polygon points="400,12 420,24 420,47 400,59 380,47 380,24" />
      <path d="M380 24 L400 36 L420 24 M400 36 V59" opacity="0.7" />
    </g>

    {/* Milestones on the pathway and triad vertices */}
    <g fill="#bd6a45" stroke="none">
      <circle cx="150.1" cy="250" r="5" />
      <circle cx="558.9" cy="161.8" r="4.5" />
      <circle cx="649.9" cy="250" r="5" />
      <circle cx="241.1" cy="338.2" r="4.5" />
      <circle cx="400" cy="250" r="4" />
      <circle cx="106" cy="357" r="4" />
      <circle cx="694" cy="357" r="4" />
    </g>
    <g opacity="0.6">
      <circle cx="150.1" cy="250" r="11" />
      <circle cx="649.9" cy="250" r="11" />
      <circle cx="400" cy="250" r="10" strokeDasharray="2 3" />
    </g>

    {/* Travelling point of light */}
    <circle className="si-bp-comet" r="4" fill="#f0a36b" stroke="none">
      <animateMotion dur="12s" repeatCount="indefinite" path={BLUEPRINT_PATH} />
    </circle>

    <g
      fill="currentColor"
      stroke="none"
      fontFamily="IBM Plex Mono, monospace"
      fontSize="10"
      letterSpacing="1.5"
      opacity="0.75"
    >
      <text x="60" y="246">01 LEARN</text>
      <text x="572" y="152">02 PRACTICE</text>
      <text x="668" y="246">03 BUILD</text>
      <text x="252" y="358">04 CAREER</text>
      <text x="412" y="276">CURIOSITY</text>
      <text x="432" y="34">MEIPORUL</text>
      <text x="40" y="380">SEYAPPADUPORUL</text>
      <text x="640" y="380">UTPORUL</text>
      <text x="318" y="438">KNOWLEDGE PATH · ∞</text>
      <text x="560" y="478">SALEM · 11.66°N 78.14°E</text>
    </g>
  </svg>
);

export interface SymphoPageHeroSpec {
  label: string;
  value: string;
  unit?: string;
  code?: string;
}

export interface SymphoPageHeroProps {
  index: string;
  eyebrow?: string;
  category?: string;
  code?: string;
  title: string;
  lede?: string;
  subtitle?: string;
  specs?: SymphoPageHeroSpec[];
  metrics?: SymphoPageHeroSpec[];
  primaryAction?: React.ReactNode;
  secondaryAction?: React.ReactNode;
  actions?: React.ReactNode;
  dark?: boolean;
  drawingCode?: string;
  badge?: string;
  children?: React.ReactNode;
}

export const SymphoPageHero: React.FC<SymphoPageHeroProps> = ({
  index,
  eyebrow,
  category,
  code,
  title,
  lede,
  subtitle,
  specs = [],
  metrics = [],
  primaryAction,
  secondaryAction,
  actions,
  dark = true,
  drawingCode = "SHEET SI—01 · SCALE 1:100",
  badge,
  children,
}) => {
  const spotRef = useRef<HTMLElement | null>(null);
  const topBarRef = useRef<HTMLDivElement | null>(null);
  const ledeRef = useRef<HTMLParagraphElement | null>(null);
  const actionsRef = useRef<HTMLDivElement | null>(null);
  const ledgerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const c1 = observeSymphoReveal(topBarRef.current, { mode: "fade" });
    const c2 = observeSymphoReveal(ledeRef.current, {
      mode: "fade",
      delay: 220,
    });
    const c3 = observeSymphoReveal(actionsRef.current, {
      mode: "fade",
      delay: 340,
    });
    const c4 = observeSymphoReveal(ledgerRef.current, {
      mode: "fade",
      delay: 260,
    });
    return () => {
      c1();
      c2();
      c3();
      c4();
    };
  }, []);

  const onPointerMove = useCallback((e: React.PointerEvent<HTMLElement>) => {
    const el = spotRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * 100;
    const my = ((e.clientY - rect.top) / rect.height) * 100;
    el.style.setProperty("--mx", `${mx.toFixed(1)}%`);
    el.style.setProperty("--my", `${my.toFixed(1)}%`);
  }, []);

  const resolvedEyebrow = eyebrow || category || "";
  const resolvedLede = lede || subtitle || "";
  const resolvedSpecs = specs.length > 0 ? specs : metrics;
  const resolvedDrawingCode = code ? `${code} · ${drawingCode}` : drawingCode;

  return (
    <section
      ref={(node) => {
        spotRef.current = node;
      }}
      onPointerMove={onPointerMove}
      className={`relative overflow-hidden border-b ${
        dark
          ? "on-dark bg-ink-900 text-limestone-50 border-limestone-100/10 blueprint-grid"
          : "bg-limestone-100 text-ink-900 border-ink-900/10 blueprint-grid-light"
      }`}
    >
      {dark && (
        <div
          aria-hidden="true"
          className="spot-light pointer-events-none absolute inset-0"
        />
      )}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-16 -bottom-24 w-[44rem] max-w-[70vw] opacity-[0.22]"
      >
        <SymphoBlueprintSvg
          className={`h-full w-full ${
            dark ? "text-limestone-100" : "text-ink-900"
          }`}
        />
      </div>

      <div className="container-page relative z-10 pt-10 pb-14 lg:pt-16 lg:pb-20">
        <div
          ref={topBarRef}
          data-reveal=""
          className="mb-8 flex flex-wrap items-center justify-between gap-4 border-b pb-5 [border-color:color-mix(in_srgb,currentColor_10%,transparent)]"
        >
          <div className="flex items-center gap-4">
            <span className="font-mono text-label text-copper-500 [.on-dark_&]:text-copper-300">
              {index}
            </span>
            <span className="sheet-label">{resolvedEyebrow}</span>
          </div>
          <div className="flex items-center gap-3 font-mono text-label opacity-70">
            {badge && (
              <span className="inline-flex items-center gap-2 rounded-pill border [border-color:color-mix(in_srgb,currentColor_20%,transparent)] px-3 py-1">
                <span className="size-1.5 rounded-pill bg-copper-400" />
                {badge}
              </span>
            )}
            <span className="hidden sm:inline">{resolvedDrawingCode}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-10 lg:grid-cols-12 lg:items-end">
          <div className="lg:col-span-8">
            <SplitHeading
              as="h1"
              text={title}
              className="text-display-xl tracking-tight"
              italicLast={2}
            />
            {resolvedLede && (
              <p
                ref={ledeRef}
                data-reveal=""
                className={`mt-6 max-w-2xl text-lede ${
                  dark ? "text-limestone-200" : "text-ink-600"
                }`}
              >
                {resolvedLede}
              </p>
            )}
            {(primaryAction || secondaryAction || actions) && (
              <div
                ref={actionsRef}
                data-reveal=""
                className="mt-8 flex flex-wrap items-center gap-4"
              >
                {primaryAction}
                {secondaryAction}
                {actions}
              </div>
            )}
          </div>

          {resolvedSpecs.length > 0 && (
            <div ref={ledgerRef} data-reveal="" className="lg:col-span-4">
              <div
                className={`sheet-frame rounded-lg border p-6 backdrop-blur-md ${
                  dark
                    ? "border-limestone-100/15 bg-ink-950/65 text-limestone-100"
                    : "border-ink-900/15 bg-limestone-50/85 text-ink-900"
                }`}
              >
                <div className="mb-4 flex items-center justify-between border-b [border-color:color-mix(in_srgb,currentColor_10%,transparent)] pb-3 font-mono text-label opacity-70">
                  <span>SPECIFICATION LEDGER</span>
                  <span className="text-copper-400">REV 2026.4</span>
                </div>
                <dl className="grid grid-cols-2 gap-x-5 gap-y-4">
                  {resolvedSpecs.map((s) => (
                    <div
                      key={s.label}
                      className="border-t [border-color:color-mix(in_srgb,currentColor_10%,transparent)] pt-3 first:border-t-0 first:pt-0 [&:nth-child(2)]:border-t-0 [&:nth-child(2)]:pt-0"
                    >
                      <dt className="font-mono text-label opacity-65">
                        {s.label}
                      </dt>
                      <dd className="mt-1 flex items-baseline gap-1.5 font-display text-xl font-normal">
                        <span>{s.value}</span>
                        {s.unit && (
                          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-copper-400">
                            {s.unit}
                          </span>
                        )}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            </div>
          )}
        </div>

        {children && <div className="mt-10">{children}</div>}
      </div>
    </section>
  );
};

export interface SymphoCtaBannerProps {
  code?: string;
  eyebrow?: string;
  title?: string;
  description?: string;
  primaryText?: string;
  primaryLabel?: string;
  primaryTo?: string;
  secondaryText?: string;
  secondaryLabel?: string;
  secondaryTo?: string;
}

export const SymphoCtaBanner: React.FC<SymphoCtaBannerProps> = ({
  code,
  eyebrow = "Begin the Conversation",
  title = "Have a learning goal, cohort, or institution to architect?",
  description = "Share your trajectory, curriculum goals, and timeline. Our academic and engineering directors respond within two business days with a structured learning blueprint.",
  primaryText,
  primaryLabel,
  primaryTo = "/courses",
  secondaryText,
  secondaryLabel,
  secondaryTo = "/contact",
}) => {
  const bannerRef = useRef<HTMLDivElement | null>(null);
  const descRef = useRef<HTMLParagraphElement | null>(null);
  const ctaColRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const c1 = observeSymphoReveal(bannerRef.current, { mode: "fade" });
    const c2 = observeSymphoReveal(descRef.current, {
      mode: "fade",
      delay: 180,
    });
    const c3 = observeSymphoReveal(ctaColRef.current, {
      mode: "fade",
      delay: 260,
    });
    return () => {
      c1();
      c2();
      c3();
    };
  }, []);

  const resolvedPrimary = primaryText || primaryLabel || "Explore all courses";
  const resolvedSecondary =
    secondaryText || secondaryLabel || "Schedule a consultation";

  return (
    <section aria-label="Start a learning journey" className="py-section-sm">
      <div className="container-page">
        <div
          ref={bannerRef}
          data-reveal=""
          className="on-dark relative overflow-hidden rounded-xl bg-ink-900 text-limestone-50 blueprint-grid"
        >
          <svg
            aria-hidden="true"
            viewBox="0 0 600 400"
            className="pointer-events-none absolute -right-24 -bottom-16 h-[28rem] w-[42rem] text-limestone-100/10"
            fill="none"
            stroke="currentColor"
            strokeWidth="1"
          >
            <path d="M40 360 L560 360" />
            <path d="M120 360 L120 140 L260 80 L260 360" />
            <path d="M260 360 L260 60 L420 60 L420 360" />
            <path d="M380 360 L380 120 L520 90 L520 360" />
            <circle cx="260" cy="60" r="4" fill="currentColor" />
            <circle cx="420" cy="60" r="4" fill="currentColor" />
            <circle cx="520" cy="90" r="4" fill="currentColor" />
          </svg>

          <div className="relative grid grid-cols-1 gap-10 p-8 sm:p-12 lg:grid-cols-12 lg:items-end lg:p-20">
            <div className="lg:col-span-8">
              <div className="mb-5 flex items-center gap-3">
                {code && (
                  <span className="font-mono text-label text-copper-300">
                    {code}
                  </span>
                )}
                <p className="sheet-label">{eyebrow}</p>
              </div>
              <SplitHeading
                as="h2"
                text={title}
                className="text-display-lg tracking-tight text-limestone-50"
                italicLast={2}
              />
              <p
                ref={descRef}
                data-reveal=""
                className="mt-6 max-w-xl text-lede text-limestone-300"
              >
                {description}
              </p>
            </div>
            <div
              ref={ctaColRef}
              data-reveal=""
              className="flex flex-col items-start gap-4 lg:col-span-4 lg:items-end"
            >
              <SymphoButton
                to={primaryTo}
                variant="on-dark"
                size="lg"
                arrow
              >
                {resolvedPrimary}
              </SymphoButton>
              <SymphoButton
                to={secondaryTo}
                variant="outline-dark"
                size="md"
              >
                {resolvedSecondary}
              </SymphoButton>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
