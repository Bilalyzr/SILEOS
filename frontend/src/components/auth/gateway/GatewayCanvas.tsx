import { useEffect, useRef } from "react";
import { prefersCalmMotion } from "./useCalmMotion";

/**
 * Living background for the auth gateway: a knowledge network whose nodes
 * settle onto a shape. Sign in → the ∞ learning path (same lemniscate as the
 * opening loader); create account → a three-petal rose, the Tamil Knowledge
 * Triad. Switching modes springs every node to its new home, so the scene
 * morphs instead of reloading.
 *
 * `focus` (0..1) brightens the network while a field is active; the cursor
 * lights and gently pushes nearby nodes. Plain 2D canvas, DPR capped, paused
 * while the tab is hidden; reduced motion draws a single still frame.
 */

type Mode = "signin" | "signup";

interface Node {
  t: number; // parameter along the shape, 0..1
  jx: number; // home jitter
  jy: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  phase: number;
  size: number;
}

const ORANGE = "253,186,116";
const TEAL = "45,212,191";

function lemniscate(t: number) {
  const a = t * Math.PI * 2;
  const d = 1 + Math.sin(a) ** 2;
  return [Math.cos(a) / d, (Math.sin(a) * Math.cos(a)) / d];
}

function triad(t: number) {
  // r = cos(3θ) traced over θ ∈ [0, π) draws three petals; rotated so one
  // petal points straight up and the other two settle left and right.
  const th = t * Math.PI;
  const r = Math.cos(3 * th);
  return [r * Math.sin(th) * 0.8, -r * Math.cos(th) * 0.8 + 0.12];
}

export function GatewayCanvas({
  mode,
  focus,
}: {
  mode: Mode;
  focus: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const modeRef = useRef(mode);
  const focusRef = useRef(focus);
  const kickRef = useRef<() => void>(() => {});

  useEffect(() => {
    modeRef.current = mode;
    kickRef.current();
  }, [mode]);
  useEffect(() => {
    focusRef.current = focus;
    kickRef.current();
  }, [focus]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduce = prefersCalmMotion();
    const finePointer = window.matchMedia("(pointer: fine)").matches;
    let W = 0;
    let H = 0;
    let dpr = 1;
    let nodes: Node[] = [];
    let raf = 0;
    let last = performance.now();
    let glowLevel = 0;
    let shapeMix = modeRef.current === "signup" ? 1 : 0;
    const mouse = { x: -9999, y: -9999, on: false };

    // Pre-rendered soft glow sprite (cheap bloom)
    const sprite = document.createElement("canvas");
    sprite.width = sprite.height = 64;
    {
      const g = sprite.getContext("2d")!;
      const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
      gr.addColorStop(0, "rgba(255,240,225,1)");
      gr.addColorStop(0.25, "rgba(253,186,116,.65)");
      gr.addColorStop(1, "rgba(194,65,12,0)");
      g.fillStyle = gr;
      g.fillRect(0, 0, 64, 64);
    }

    // Where the shape sits: left two-thirds on desktop (the form floats on
    // the right), upper middle on narrow screens.
    const frame = () => {
      const wide = W >= 1024;
      const cx = wide ? W * 0.36 : W * 0.5;
      // Narrow screens: the shape floats in the band between the top bar
      // and the headline, clear of the form.
      const cy = wide ? H * 0.52 : Math.min(H * 0.17, 150);
      const scale = wide ? Math.min(W * 0.3, H * 0.42) : Math.min(W * 0.4, 150);
      return { cx, cy, scale };
    };

    const home = (n: Node, mix: number) => {
      const { cx, cy, scale } = frame();
      const [lx, ly] = lemniscate(n.t);
      const [tx, ty] = triad(n.t);
      const x = lx + (tx - lx) * mix;
      const y = ly + (ty - ly) * mix;
      return [cx + (x + n.jx) * scale, cy + (y + n.jy) * scale];
    };

    const build = () => {
      const count = W >= 1024 ? 110 : W >= 640 ? 76 : 48;
      nodes = Array.from({ length: count }, (_, i) => {
        const n: Node = {
          t: (i + Math.random() * 0.6) / count,
          jx: (Math.random() - 0.5) * 0.12,
          jy: (Math.random() - 0.5) * 0.12,
          x: 0,
          y: 0,
          vx: 0,
          vy: 0,
          phase: Math.random() * Math.PI * 2,
          size: 0.6 + Math.random() * 1.1,
        };
        const [hx, hy] = home(n, shapeMix);
        // Start scattered so the network assembles on arrival
        n.x = reduce ? hx : hx + (Math.random() - 0.5) * W * 0.5;
        n.y = reduce ? hy : hy + (Math.random() - 0.5) * H * 0.5;
        return n;
      });
    };

    const size = () => {
      const rect = canvas.getBoundingClientRect();
      W = Math.max(1, rect.width);
      H = Math.max(1, rect.height);
      dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = Math.round(W * dpr);
      canvas.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      build();
    };

    const draw = (now: number, dt: number) => {
      const target = modeRef.current === "signup" ? 1 : 0;
      shapeMix += (target - shapeMix) * Math.min(1, dt / 520);
      if (reduce) shapeMix = target;
      glowLevel += (focusRef.current - glowLevel) * Math.min(1, dt / 260);
      const lit = 0.55 + 0.45 * glowLevel;

      ctx.clearRect(0, 0, W, H);

      // Ambient light behind the shape, tinted by mode
      const { cx, cy, scale } = frame();
      const amb = ctx.createRadialGradient(cx, cy, 0, cx, cy, scale * 1.9);
      amb.addColorStop(0, `rgba(194,65,12,${0.16 + 0.12 * glowLevel})`);
      amb.addColorStop(0.55, `rgba(30,45,72,${0.18 + 0.1 * shapeMix})`);
      amb.addColorStop(1, "rgba(15,26,46,0)");
      ctx.fillStyle = amb;
      ctx.fillRect(0, 0, W, H);

      // Move nodes: spring toward home, drift, cursor push
      const t = now / 1000;
      for (const n of nodes) {
        const [hx, hy] = home(n, shapeMix);
        const drift = reduce ? 0 : 3.2;
        const gx = hx + Math.cos(t * 0.6 + n.phase) * drift;
        const gy = hy + Math.sin(t * 0.8 + n.phase) * drift;
        n.vx += (gx - n.x) * 0.012;
        n.vy += (gy - n.y) * 0.012;
        if (mouse.on) {
          const dx = n.x - mouse.x;
          const dy = n.y - mouse.y;
          const d2 = dx * dx + dy * dy;
          if (d2 < 120 * 120 && d2 > 1) {
            const f = (1 - Math.sqrt(d2) / 120) * 0.9;
            n.vx += (dx / Math.sqrt(d2)) * f;
            n.vy += (dy / Math.sqrt(d2)) * f;
          }
        }
        n.vx *= 0.86;
        n.vy *= 0.86;
        if (reduce) {
          n.x = gx;
          n.y = gy;
        } else {
          n.x += n.vx * (dt / 16.7);
          n.y += n.vy * (dt / 16.7);
        }
      }

      // Links between near neighbours
      const maxD = W >= 1024 ? 92 : 70;
      ctx.lineWidth = 1;
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d2 = dx * dx + dy * dy;
          if (d2 > maxD * maxD) continue;
          const k = 1 - Math.sqrt(d2) / maxD;
          ctx.strokeStyle = `rgba(${ORANGE},${(k * 0.32 * lit).toFixed(3)})`;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }

      // Nodes, with a travelling pulse along the path
      const pulse = (t * 0.09) % 1;
      for (const n of nodes) {
        let dp = Math.abs(n.t - pulse);
        dp = Math.min(dp, 1 - dp);
        const hot = reduce ? 0 : Math.max(0, 1 - dp * 18);
        let near = 0;
        if (mouse.on) {
          const d = Math.hypot(n.x - mouse.x, n.y - mouse.y);
          near = Math.max(0, 1 - d / 160);
        }
        const r = n.size * (1.6 + hot * 2.2 + near * 1.4);
        const alpha = Math.min(1, (0.45 + hot * 0.55 + near * 0.4) * lit);
        ctx.globalAlpha = alpha;
        ctx.drawImage(sprite, n.x - r * 4, n.y - r * 4, r * 8, r * 8);
        ctx.globalAlpha = 1;
        ctx.fillStyle = hot > 0.3 ? `rgba(${TEAL},${alpha})` : `rgba(255,236,218,${alpha})`;
        ctx.beginPath();
        ctx.arc(n.x, n.y, Math.max(0.8, r * 0.45), 0, Math.PI * 2);
        ctx.fill();
      }

      // Cursor light
      if (mouse.on && finePointer) {
        const cg = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, 220);
        cg.addColorStop(0, "rgba(253,186,116,0.10)");
        cg.addColorStop(1, "rgba(253,186,116,0)");
        ctx.fillStyle = cg;
        ctx.fillRect(mouse.x - 220, mouse.y - 220, 440, 440);
      }
    };

    const loop = (now: number) => {
      raf = 0;
      const dt = Math.min(48, now - last);
      last = now;
      draw(now, dt);
      if (!reduce && !document.hidden) raf = requestAnimationFrame(loop);
    };
    const kick = () => {
      if (reduce) {
        draw(performance.now(), 1000);
        return;
      }
      if (!raf && !document.hidden) {
        last = performance.now();
        raf = requestAnimationFrame(loop);
      }
    };
    kickRef.current = kick;

    const onMove = (e: PointerEvent) => {
      if (!finePointer) return;
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
      mouse.on = true;
    };
    const onLeave = () => {
      mouse.on = false;
    };
    const onVis = () => kick();
    const ro = new ResizeObserver(() => {
      size();
      kick();
    });

    size();
    ro.observe(canvas);
    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerleave", onLeave);
    document.addEventListener("visibilitychange", onVis);
    kick();

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerleave", onLeave);
      document.removeEventListener("visibilitychange", onVis);
      kickRef.current = () => {};
    };
  }, []);

  return <canvas ref={canvasRef} aria-hidden="true" className="ag-canvas" />;
}
