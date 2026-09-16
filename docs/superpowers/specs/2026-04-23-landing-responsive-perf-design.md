# Landing-page Responsiveness + Performance — Design Spec

**Date:** 2026-04-23
**Status:** Approved, scope locked

## Problem

Landing pages (`Home`, `About`, `Contact`) are slow and break on smaller viewports. Root causes identified:

- Home uses Three.js + GLTF loader synchronously on mount → blocks first paint, kills mobile battery.
- `Home.tsx` is 837 lines of imperative scene/animation code sitting on the critical path. Nothing below-the-fold is code-split.
- Section CSS modules have uneven media-query coverage: AboutSection=4, CategoriesSection=2, PartnersSection=1, StaticPartnersSection=1, NewsSection=3, TestimonialsSection=3, HeroSection=5, home.css=19. Mobile cases aren't consistently handled.
- Images rendered without explicit width/height → layout shift.
- Lenis smooth-scroll + framer-motion run whether the user wants them or not (`prefers-reduced-motion` ignored).

## Scope

**Responsiveness + performance only. No visual, color, or content changes.**

All existing features stay on every device — the 3D hero, scroll animations, Lenis smooth scroll, framer-motion effects. Gains come from loading strategy + CSS coverage + respecting device capability, not from removing features.

## Out of scope
- Colors, typography, copy, layout reorganisation.
- Removing any library.
- Component visual redesign.
- Backend changes.

## Tasks

### T1 — Split `Home.tsx` into section components

The file mixes Three.js scene management + 10+ JSX sections in one 837-line component. Split so each section is its own file under `src/components/home/`:

- `HeroSectionHome.tsx` (the 3D + hero copy block — new, separate from the existing reusable `HeroSection.tsx`)
- Reuse existing `AboutSection`, `CategoriesSection`, `NewsSection`, `PartnersSection`, `StaticPartnersSection`, `TestimonialsSection`, `ScrollStack` (already separate).
- New small files for any inline sections in Home.tsx: `CardSwapSection.tsx`, `TeamSection.tsx`, `CTASection.tsx`, `BlogPreviewSection.tsx`, `NewsletterSection.tsx`.

`Home.tsx` shrinks to a ~60-line shell that renders them.

### T2 — Lazy-load below-the-fold sections

Top of the fold (eagerly loaded): `HeroSectionHome` + maybe one section immediately below.

Everything else uses `React.lazy` + `<Suspense fallback={<SectionSkeleton />}>`. Skeleton is a simple `min-height` placeholder sized to the section so there's no layout shift when the chunk loads.

Result: initial JS bundle for the landing page drops dramatically (Three.js stays, but in its own chunk loaded on-demand when the hero mounts).

### T3 — Defer Three.js + GLTF loader work

Currently the Three.js scene is set up synchronously in a `useEffect` at Home mount. Move to:

- Dynamic `import('three')` and `import('three/examples/jsm/loaders/GLTFLoader.js')` inside the effect so the bundle splits.
- Use `requestIdleCallback` (fallback `setTimeout(..., 250)`) to schedule scene initialization after first paint finishes.
- IntersectionObserver pauses the render loop when the hero is offscreen; resumes when visible.
- Respect `prefers-reduced-motion: reduce` → still render the scene, just drop the per-frame animation loop (static frame).

### T4 — Image and media hygiene

Audit every `<img>` in the landing pages and section components. For each:
- Add `loading="lazy"` (except hero's first image, which is eager).
- Add explicit `width` and `height` attributes (or `aspect-ratio` CSS) to stop CLS.
- Add `decoding="async"`.
- Third-party images (Cloudinary, etc.): add `fetchpriority` hints where applicable.

### T5 — Responsive CSS audit

For each of these `*.module.css` / `home.css` files:
- `HeroSection.module.css`
- `AboutSection.module.css`
- `CategoriesSection.module.css`
- `NewsSection.module.css`
- `PartnersSection.module.css`
- `StaticPartnersSection.module.css`
- `TestimonialsSection.module.css`
- `ScrollStack.css`
- `pages/home.css`

Ensure three consistent breakpoints are covered: **≤640px (mobile)**, **641–1024px (tablet)**, **≥1025px (desktop)**. For each section verify:
- No horizontal overflow on 320px-wide viewport.
- Grid/flex layouts collapse to one column at mobile.
- Font sizes scale down — absolute px values above 24 get a mobile override.
- Touch targets ≥44×44px.
- No `position: absolute` that escapes parent bounds.

Don't redesign — only add/repair the missing media queries so existing layouts work on every size.

### T6 — Respect `prefers-reduced-motion`

Add this at the top of `pages/home.css` (or a shared `responsive.css`):

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

Features stay visible; expensive animations just settle into their final state instantly on devices where the user requested reduced motion.

### T7 — Verification before merge

Run `docker compose up` locally, measure:
- Lighthouse mobile score before and after the pass (target: >75 performance on mobile).
- First Contentful Paint < 2s on throttled 3G.
- Visible layout shift = 0 on Home.
- Verify all sections render correctly on mobile Safari-like viewport (Chrome DevTools iPhone 13 preset).

## Risks

- **Splitting Home.tsx might break state wiring.** Mitigation: keep shared state at the top of `Home.tsx`, pass via props. No context needed.
- **Dynamic Three.js import may flash empty hero briefly.** Mitigation: the skeleton fallback is a CSS gradient matching the existing hero background so the transition is invisible.
- **IntersectionObserver's pause may cause a scene jump when user scrolls back.** Mitigation: resume from the last rendered frame, not reset.

## Non-goals
- No new libraries added.
- No tests written (no existing test suite).
- No backend or API surface changes.

## Execution plan

Single subagent task. I'll dispatch after spec review.
