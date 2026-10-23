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
      ? "bg-copper-500 text-[#51230d] font-bold hover:text-limestone-50 [--fill:#9a390b] border border-[#ffbe86]/70 shadow-[0_7px_20px_rgba(222,121,37,0.24),inset_0_1px_0_#ffffff]"
      : variant === "outline-dark" || variant === "ghost-dark"
      ? "bg-transparent text-limestone-50 border border-limestone-100/35 hover:border-copper-300 hover:text-[#51230d] [--fill:var(--color-copper-300)]"
      : variant === "outline"
      ? "bg-[#fff8ef] text-[#843711] border border-[#edc7a7] hover:border-[#9a390b] hover:text-limestone-50 [--fill:#9a390b]"
      : variant === "copper"
      ? "bg-copper-500 text-[#51230d] font-bold hover:text-limestone-50 [--fill:#9a390b] border border-[#ffbe86]/70 shadow-[0_7px_20px_rgba(222,121,37,0.22),inset_0_1px_0_#ffffff]"
      : "bg-copper-500 text-[#51230d] font-bold hover:text-limestone-50 [--fill:#9a390b] border border-[#ffbe86]/70 shadow-[0_7px_20px_rgba(222,121,37,0.22),inset_0_1px_0_#ffffff]";

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
    <g opacity="0.2" strokeDasharray="3 5">
      <line x1="60" y1="90" x2="740" y2="90" />
      <line x1="60" y1="250" x2="740" y2="250" />
      <line x1="60" y1="410" x2="740" y2="410" />
      <line x1="180" y1="40" x2="180" y2="460" />
      <line x1="400" y1="40" x2="400" y2="460" />
      <line x1="620" y1="40" x2="620" y2="460" />
    </g>
    {/* Orbital Knowledge Rings */}
    <ellipse
      cx="400"
      cy="250"
      rx="280"
      ry="95"
      strokeDasharray="6 4"
      opacity="0.45"
    />
    <ellipse
      cx="400"
      cy="250"
      rx="220"
      ry="155"
      transform="rotate(-18 400 250)"
      opacity="0.35"
    />
    {/* AR/VR Spatial Learning Glasses Chassis & Dual Waveguide Lenses */}
    <path
      d="M175 235 C175 190, 240 175, 390 182 L410 182 C560 175, 625 190, 625 235 L620 292 C616 328, 540 338, 455 322 C432 316, 416 286, 400 286 C384 286, 368 316, 345 322 C260 338, 184 328, 180 292 Z"
      strokeWidth="1.6"
    />
    {/* Left & Right Waveguide Optical Lenses */}
    <rect x="202" y="200" width="166" height="106" rx="28" strokeWidth="1.3" />
    <rect x="432" y="200" width="166" height="106" rx="28" strokeWidth="1.3" />
    {/* Inner Fresnel / Waveguide HUD Reticles */}
    <circle cx="285" cy="253" r="34" strokeDasharray="4 3" opacity="0.65" />
    <circle cx="515" cy="253" r="34" strokeDasharray="4 3" opacity="0.65" />
    <path d="M265 253 H305 M285 233 V273" opacity="0.6" />
    <path d="M495 253 H535 M515 233 V273" opacity="0.6" />
    {/* Articulated Temple Compute Arms */}
    <path d="M175 225 L110 165 L95 178 L168 258" opacity="0.75" />
    <path d="M625 225 L690 165 L705 178 L632 258" opacity="0.75" />
    {/* Projected Spatial Polyhedron above Bridge */}
    <polygon
      points="400,72 452,102 452,154 400,184 348,154 348,102"
      strokeWidth="1.2"
    />
    <path
      d="M400 72 L400 184 M348 102 L452 154 M452 102 L348 154"
      opacity="0.5"
    />
    {/* Projection Frustum Rays */}
    <path
      d="M285 200 L348 128 M515 200 L452 128"
      strokeDasharray="3 4"
      opacity="0.55"
    />
    <circle cx="285" cy="253" r="4" fill="#bd6a45" stroke="none" />
    <circle cx="515" cy="253" r="4" fill="#bd6a45" stroke="none" />
    <circle cx="400" cy="72" r="4.5" fill="#bd6a45" stroke="none" />
    <circle cx="175" cy="235" r="4" fill="#bd6a45" stroke="none" />
    <circle cx="625" cy="235" r="4" fill="#bd6a45" stroke="none" />
    <g
      fill="currentColor"
      stroke="none"
      fontFamily="IBM Plex Mono, monospace"
      fontSize="10"
      opacity="0.7"
    >
      <text x="72" y="82">
        FOV 110° · DUAL WAVEGUIDE
      </text>
      <text x="72" y="242">
        OPTICAL AXIS ±0.00mm
      </text>
      <text x="72" y="402">
        PEDESTAL Ø 240mm
      </text>
      <text x="485" y="82">
        MEIPORUL AR/VR LEARNING RIG
      </text>
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
        className="pointer-events-none absolute -right-20 -bottom-16 w-[38rem] max-w-[65vw] opacity-20"
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
