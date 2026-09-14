# ASTRA DESIGN DIRECTIVE — Gradient Glassmorphism

**Scope:** binding visual style for **every page** Astra generates in this product. Apply on new pages without being asked. Do not invent colors, radii, or fonts outside this file.

---

## 1. The idea in one paragraph

Every page sits on a soft, out-of-focus color field. All UI floats above it as translucent frosted panels with a bright 1px top edge and a wide, low-opacity drop shadow. Depth is communicated by **how opaque a panel is**, not by how heavy its border is. Content that must be *read* — tables, forms, numbers, checkout, quizzes — sits on the most opaque tier. Decoration sits on the most transparent tier. Nothing important ever floats on glass thin enough to read the background through.

---

## 2. Tokens (copy verbatim)

```css
:root{
  /* ink */
  --ink:        #17233a;   /* headings, primary body */
  --ink-2:      #3d4c68;   /* secondary body */
  --ink-3:      #5b6a86;   /* labels, captions (min 12px) */
  --ink-inv:    #ffffff;

  /* brand */
  --accent:      #f97316;  /* primary orange — fills, not text */
  --accent-deep: #b23c05;  /* orange for TEXT and button bg under white text */
  --accent-2:    #fbbf24;
  --violet: #6d4aff;
  --teal:   #0d8f9e;
  --blue:   #2159d8;
  --pink:   #d81e63;
  --navy:   #0b2540;

  /* status (all AA on glass) */
  --ok:#047a5b; --warn:#a4620a; --bad:#c62525; --info:#0b6fa8;

  /* glass tiers */
  --glass-1: rgba(255,255,255,.52);   /* ambient   */
  --glass-2: rgba(255,255,255,.70);   /* content   */
  --glass-3: rgba(255,255,255,.88);   /* work      */
  --glass-edge: rgba(255,255,255,.85);
  --hairline:  rgba(23,35,58,.10);

  --blur-1: blur(18px) saturate(160%);
  --blur-2: blur(24px) saturate(168%);
  --blur-3: blur(30px) saturate(175%);

  /* elevation */
  --shadow-1: 0 2px 8px rgba(18,28,48,.05);
  --shadow-2: 0 12px 32px rgba(18,28,48,.09);
  --shadow-3: 0 24px 60px rgba(18,28,48,.13);
  --lift: inset 0 1px 0 rgba(255,255,255,.75);

  /* radii + rhythm */
  --r-s:12px; --r-m:20px; --r-l:28px; --r-pill:999px;
  --sp:4px;  /* all spacing = multiples of 4 */
}
```

### Gradient field — one per page, fixed, behind everything

```css
body{
  margin:0; color:var(--ink);
  font-family:'Plus Jakarta Sans', system-ui, sans-serif;
  background:#f6f8fc;
}
body::before{
  content:''; position:fixed; inset:0; z-index:0; pointer-events:none;
  background:
    radial-gradient(60% 55% at 12% 8%,  rgba(109,74,255,.30), transparent 70%),
    radial-gradient(55% 50% at 88% 14%, rgba(13,143,158,.26), transparent 72%),
    radial-gradient(70% 60% at 70% 92%, rgba(249,115,22,.24), transparent 74%),
    linear-gradient(160deg,#eef3fb,#fdf6f0);
  filter:saturate(115%);
}
```

**Per-page hue rotation** — keep the same three-blob geometry, swap the accent blob so pages feel distinct but related:

| Page family | Lead hue | Second |
|---|---|---|
| Dashboard / home | orange | violet |
| Learn / lesson | teal | blue |
| Catalog / browse | violet | orange |
| Admin / settings | blue | navy |
| Billing / checkout | orange | pink |

Max two saturated hues per page plus the neutral gradient. Never a full-page linear rainbow gradient.

---

## 3. Glass tiers — the load-bearing rule

| Tier | Background | Blur | Use for | Body copy allowed |
|---|---|---|---|---|
| 1 Ambient | `--glass-1` | `--blur-1` | nav rails, chips, badges, tab bars, decorative panels | no — labels only |
| 2 Content | `--glass-2` | `--blur-2` | cards, list rows, section panels, modals | yes |
| 3 Work | `--glass-3` | `--blur-3` | tables, forms, inputs, checkout, quizzes, code, any number the user acts on | yes |

Panel recipe:

```css
.glass{
  background:var(--glass-2);
  backdrop-filter:var(--blur-2);
  -webkit-backdrop-filter:var(--blur-2);
  border:1px solid var(--hairline);
  border-radius:var(--r-m);
  box-shadow:var(--shadow-2), var(--lift);
}
```

- Never nest glass in glass more than **two levels**. A tier-3 panel inside a tier-2 card is the deepest legal stack; inside that, use solid `#fff` or a flat tint.
- Every glass panel gets `--lift` (the bright inner top edge). That highlight is what reads as "glass" — without it panels look like flat translucent boxes.
- Always ship the `-webkit-` prefix, and a solid fallback:

```css
@supports not (backdrop-filter: blur(2px)){
  .glass{ background:rgba(255,255,255,.94); }
}
```

---

## 4. Type

- Display / headings: **Plus Jakarta Sans**, 700, `letter-spacing:-.02em`, `text-wrap:balance`.
- Body / UI: **Plus Jakarta Sans**, 400–600, `line-height:1.65`, `text-wrap:pretty`.
- Numerals / code: **JetBrains Mono**, 500.
- Scale (px): 11 · 12.5 · 14 · 15.5 · 17 · 21 · 27 · 34 · 44. Nothing below 11px, and 11–12px only for uppercase tracked labels at `--ink-3`.
- Uppercase label: `font:600 11px; letter-spacing:.09em; text-transform:uppercase; color:var(--ink-3)`.

---

## 5. Components

**Primary button** — solid, never translucent:
```css
background:var(--accent-deep); color:#fff; border:0;
padding:11px 20px; border-radius:var(--r-pill);
font:600 14px/1 'Plus Jakarta Sans',sans-serif;
box-shadow:0 10px 22px rgba(178,60,5,.28);
```
Hover: `filter:brightness(1.08)`. Active: `transform:translateY(1px)`.

**Secondary button** — tier-2 glass, `1px solid var(--hairline)`, text `--ink`.

**Input / select** — tier-3 glass, `--r-s`, `1px solid var(--hairline)`; focus adds `box-shadow:0 0 0 3px rgba(249,115,22,.28)` and border `--accent-deep`. Never a translucent input on a photo or blob.

**Card** — tier 2, `--r-m`, `padding:22px`, gap-based internal layout.

**Table** — wrap in tier-3 glass, `--r-m`, `overflow:hidden`. Header row `rgba(23,35,58,.04)`, uppercase label style. Row separators `1px solid var(--hairline)`. Zebra striping is not used.

**Nav rail** — tier 1, sticky, `--r-l`. Active item: `background:rgba(249,115,22,.14)`, text `--accent-deep`, plus a 3px `--accent` left indicator inside the radius.

**Chip / badge** — tier 1, `--r-pill`, `padding:6px 13px`, 11px 600 label. Status chips use the status hue at 14% alpha with the full-opacity hue as text.

**Modal / sheet** — tier 3, `--r-l`, `--shadow-3`, over a `rgba(11,37,64,.34)` scrim with `backdrop-filter:blur(6px)`.

**Layout** — flex/grid with `gap` only, never margin-spaced inline siblings. Content max-width 1200px. Fluid: `minmax(0,1fr)` tracks, no fixed heights on text boxes.

**Motion** — 160ms `cubic-bezier(.2,.7,.3,1)` on opacity/transform only. No animated gradients, no shimmer, no floating blobs. Respect `prefers-reduced-motion`.

---

## 6. Accessibility — non-negotiable

1. Body text ≥ **4.5:1** against the *composited* panel, not against pure white. Headline-scale (≥27px, 700) may use 3:1.
2. Orange as **text** is always `--accent-deep` (#b23c05). `#f97316` is a fill color only.
3. Body copy is never placed on tier 1, and never directly on the gradient field.
4. Text on glass is always full opacity — never `opacity:.7` or `color-mix` mutes for hierarchy; step down the ink token instead.
5. Focus is always visible: 3px accent ring, never `outline:none` alone.
6. Interactive targets ≥ 44px on touch layouts.

---

## 7. Do not

- Full-page saturated gradients behind text, or gradient text fills.
- Gradient borders, glow rings, neon outlines.
- Dark-glass panels mixed into the light system.
- Heavy 2px+ borders — depth comes from opacity and shadow.
- Emoji as UI iconography.
- More than two saturated hues per page.
- Blur radius above 30px (it turns the field to mud and costs frames).
- `backdrop-filter` on scrolling list items — put it on the container.

---

## 8. Astra's per-page checklist

- [ ] Fixed gradient field applied, hue pair chosen from the page-family table.
- [ ] Every panel assigned a tier, and no body copy on tier 1.
- [ ] Glass nesting ≤ 2 deep.
- [ ] All panels carry `--lift` and a `-webkit-` prefixed blur.
- [ ] `@supports not (backdrop-filter)` fallback present.
- [ ] Primary CTA solid `--accent-deep`; no translucent buttons.
- [ ] Tables/forms on tier 3.
- [ ] Contrast spot-checked on the lightest and darkest region of the field.
- [ ] Layout reflows below 900px without fixed widths.
