# CBSE Virtual Labs · Classes 6–12
Interactive Science & Math simulations mapped to CBSE chapters, packaged for LMS use.
**38 labs (29 classic · 7 ✦3D · 2 🥽XR) · full 6–12 curriculum map · 233 chapters catalogued · 100% offline-capable (XR needs a headset).**

---

## What's inside

| Area | Contents |
|---|---|
| **🧭 Learning Path** (`journey.html`) | Every CBSE chapter for classes 6–12 — 233 chapters with difficulty tiers (Foundation / Core / Advanced), per-chapter resource pack (concept notes · solved examples · practice quiz · board-pattern questions), and lab links |
| **Mathematics** | Fractions Explorer, Pythagoras Explorer, Line Explorer, Quadratic Explorer, Probability Lab |
| **Science (6–10)** | Electric Circuits, Acids/Bases & pH, Light: Reflection & Refraction, Distance–Time Graphs, Plant & Animal Cell, Predator–Prey Ecosystem |
| **Physics (11–12)** | Projectile Motion, Simple Pendulum, Wave Motion |
| **Chemistry** | Acid–Base Titration, Ideal Gas Lab |
| **Biology** | Punnett Squares Genetics, Photosynthesis |
| **✦ 3D labs (WebGL)** | **Solar System 3D** (orbiting planets, Saturn's rings, mission clock), **Atom Builder 3D** (elements 1–20, shells K-L-M-N, isotopes), **DNA Double Helix 3D** (base pairing + unzip-to-replicate), **Molecule Viewer 3D** (ball-and-stick: H₂O, CO₂, CH₄, NH₃, ethanol with true bond angles) |

The 3D labs use a **locally bundled copy of Three.js (MIT licence)** in `assets/three.min.js`
— no CDN, no internet needed, commercially usable. Camera controls are custom
(drag = rotate, scroll = zoom).

---

## 🥽 XR / VR / AR labs (WebXR)

| Lab | Modes | What students do |
|---|---|---|
| **Solar System XR** | VR | Stand on the Sun at room scale; planets orbit around them; point a controller at a planet and pull the trigger for a floating fact card |
| **Molecule XR** | VR + AR | Walk around giant ball-and-stick molecules (H₂O, CO₂, CH₄, NH₃, ethanol); in AR the molecule appears **on the student's desk** through the camera |

**How to run them:**
1. **Meta Quest / any WebXR headset** — open the lab in the headset's browser (Quest Browser), tap *Enter VR*. Hosting must be **HTTPS** (LMS hosting usually already is; `localhost` also works).
2. **Phone AR** (WebXR-capable Android phones) — tap *Enter AR* and move the phone to place the molecule on a table.
3. **No headset?** Both labs run fully in flat 3D with mouse/touch — nothing is locked behind hardware. The XR buttons show a clear status when no device is found.

**Integration layer:** `assets/xrkit.js` (hand-written WebXR layer — session button with
capability detection, VR/AR session handling, controller rigs with laser pointers,
in-world HUD panels). Reuse it to XR-enable any future lab: init with `L3.init(canvas, {xr:true})`,
then `XRK.button(...)` + `XRK.controllers(...)`.


Each lab is a single HTML file in `labs/<subject>/` plus two shared files in `assets/`.

---

## Option 1 — Import as a SCORM package (Moodle, Canvas, Blackboard…)

1. Upload the **whole zip** (this folder) as a *SCORM package*.
2. That's it. The included `imsmanifest.xml` + `scorm_adapter.js` register completion
   automatically. Students see the full library in one activity.

## Option 2 — Embed a single lab in any LMS page

Host the folder anywhere (school server, GitHub Pages, Netlify), then paste an iframe
into your LMS page / lesson:

```html
<iframe src="https://YOUR-HOST/labs/science/electric-circuits.html"
        width="100%" height="640" frameborder="0" allowfullscreen></iframe>
```

The **"Embed in LMS" button** on the library home page copies a ready-made snippet
for every lab with your exact URL.

## Option 3 — Google Classroom / plain link

Share the hosted URL of any lab (or of `index.html`) as a link or assignment resource.
Google Sites: use *Insert → Embed → by URL*.

## Offline / classroom use

Copy the folder to any laptop and open `index.html` — no internet needed. Each lab
file is self-rendering; only the two shared `assets` files must sit beside the `labs`
folder.

---

## Customising & branding

- **Colours/logo:** edit the `:root` variables at the top of `assets/labkit.css`
  (`--brand`, etc.) — every lab re-skins instantly.
- **Names:** each lab's `<h1>` sits in the page header; change freely.
- **Adding a lab:** copy an existing file in `labs/<subject>/`, edit it, and add one
  entry to the `LABS` array at the top of `index.html` (plus one `<file>` line in
  `imsmanifest.xml` if you use SCORM).

## Pedagogy notes

Every lab follows the same pattern: *explore freely → observe linked representations →
predict → check the "Think about it" prompts*. Suggested classroom flow:

1. Demo one case on the projector (2 min)
2. Pairs explore with the prompt card (5 min)
3. Students predict, then verify with the simulation (5 min)
4. Quick exit question from the "Think about it" box

## Licence & ownership

All code in this package was written originally for this project — it contains **no
third-party code, no CDN calls, no analytics, no tracking**. You are free to use,
modify, brand and host it for your institution, including commercially.
