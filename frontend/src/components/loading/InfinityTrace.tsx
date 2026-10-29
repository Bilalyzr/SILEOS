/**
 * In-app loading state: the ∞ learning pathway draws itself, then a point of
 * light travels it while knowledge nodes along the path ignite in turn.
 * Pairs with the opening sequence in index.html. `data-app-loading` tells
 * that sequence the app is still on a loading screen, so it waits for real
 * content before revealing. Reduced motion: a still path plus the label.
 */

// Lemniscate of Bernoulli (a = 98) sampled at 96 points — symmetric loops,
// round ends, a true crossing at the centre. (The earlier hand-written
// cubic version had a lopsided right loop that ran past the viewBox.)
const PATH =
  "M98.0 0.0 L97.4 6.4 L95.5 12.5 L92.6 18.1 L88.7 23.0 L84.1 27.0 L79.0 30.2 L73.5 32.5 L67.9 33.9 L62.3 34.6 L56.7 34.5 L51.4 33.9 L46.2 32.7 L41.3 31.0 L36.6 29.0 L32.2 26.8 L28.0 24.2 L24.0 21.5 L20.2 18.7 L16.6 15.7 L13.1 12.7 L9.7 9.6 L6.5 6.4 L3.2 3.2 L0.0 0.0 L-3.2 -3.2 L-6.5 -6.4 L-9.7 -9.6 L-13.1 -12.7 L-16.6 -15.7 L-20.2 -18.7 L-24.0 -21.5 L-28.0 -24.2 L-32.2 -26.8 L-36.6 -29.0 L-41.3 -31.0 L-46.2 -32.7 L-51.4 -33.9 L-56.7 -34.5 L-62.3 -34.6 L-67.9 -33.9 L-73.5 -32.5 L-79.0 -30.2 L-84.1 -27.0 L-88.7 -23.0 L-92.6 -18.1 L-95.5 -12.5 L-97.4 -6.4 L-98.0 -0.0 L-97.4 6.4 L-95.5 12.5 L-92.6 18.1 L-88.7 23.0 L-84.1 27.0 L-79.0 30.2 L-73.5 32.5 L-67.9 33.9 L-62.3 34.6 L-56.7 34.5 L-51.4 33.9 L-46.2 32.7 L-41.3 31.0 L-36.6 29.0 L-32.2 26.8 L-28.0 24.2 L-24.0 21.5 L-20.2 18.7 L-16.6 15.7 L-13.1 12.7 L-9.7 9.6 L-6.5 6.4 L-3.2 3.2 L-0.0 0.0 L3.2 -3.2 L6.5 -6.4 L9.7 -9.6 L13.1 -12.7 L16.6 -15.7 L20.2 -18.7 L24.0 -21.5 L28.0 -24.2 L32.2 -26.8 L36.6 -29.0 L41.3 -31.0 L46.2 -32.7 L51.4 -33.9 L56.7 -34.5 L62.3 -34.6 L67.9 -33.9 L73.5 -32.5 L79.0 -30.2 L84.1 -27.0 L88.7 -23.0 L92.6 -18.1 L95.5 -12.5 L97.4 -6.4Z";
// Nodes lie on the curve in the order the path is drawn (it starts at the
// right tip); each delay is when the drawing line reaches that node under
// the 1.4s cubic-bezier(.65,0,.35,1) draw, so nodes ignite as it passes.
const NODES: Array<[number, number, number]> = [
  [98, 0, 0],
  [62.3, 34.6, 0.38],
  [0, 0, 0.56],
  [-62.3, -34.6, 0.66],
  [-98, 0, 0.7],
  [-62.3, 34.6, 0.74],
  [62.3, -34.6, 1.02],
];

export function InfinityTrace({
  label = "Preparing your workspace",
  fullscreen = false,
}: {
  label?: string;
  fullscreen?: boolean;
}) {
  return (
    <div
      className={`si-trace ${fullscreen ? "si-trace-full" : ""}`}
      role="status"
      aria-live="polite"
      data-app-loading=""
    >
      <svg viewBox="-112 -48 224 96" aria-hidden="true" className="si-trace-svg">
        <path d={PATH} className="si-trace-rail" />
        <path d={PATH} className="si-trace-draw" pathLength={100} />
        <path d={PATH} className="si-trace-comet" pathLength={100} />
        {NODES.map(([x, y, delay], i) => (
          <circle
            key={i}
            cx={x}
            cy={y}
            r={3.2}
            className="si-trace-node"
            style={{ animationDelay: `${delay}s` }}
          />
        ))}
      </svg>
      <span className="si-trace-label">{label}</span>
    </div>
  );
}
