/**
 * Schematic animal cell on a 0-100 × 0-100 viewBox. Hotspot coordinates in
 * backend/app/routers/virtual_labs.py CELL_IDENTIFY are expressed in this
 * same box, so each organelle below is drawn centred on its hotspot.
 * Pure presentation — no labels (the lab asks the student to find them).
 */
export function CellDiagram({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet" className={className} role="img" aria-label="Animal cell diagram">
      {/* cytoplasm + membrane */}
      <ellipse cx="50" cy="50" rx="44" ry="36" fill="#fdebd3" stroke="#d97706" strokeWidth="1.6" />
      <ellipse cx="50" cy="50" rx="41.5" ry="33.5" fill="none" stroke="#f59e0b" strokeWidth="0.5" strokeDasharray="1.2 1.2" />

      {/* nucleus (60,50 r13) + nucleolus (63,47 r4) */}
      <circle cx="60" cy="50" r="13" fill="#d8ccf7" stroke="#6d28d9" strokeWidth="1.2" />
      <circle cx="60" cy="50" r="11.2" fill="none" stroke="#8b5cf6" strokeWidth="0.5" strokeDasharray="1 1" />
      <circle cx="63" cy="47" r="4" fill="#7c3aed" />

      {/* rough ER (81,52): wavy membranes with ribosome dots */}
      {[42, 47, 52, 57, 62].map((y) => (
        <path key={y} d={`M 75 ${y} q 3 -2 6 0 t 6 0`} fill="none" stroke="#2563eb" strokeWidth="1.1" />
      ))}
      {[[77, 41], [83, 41], [79, 46.5], [85, 46.5], [77, 51], [83, 51], [79, 56.5], [85, 56.5], [77, 61], [83, 61]].map(([x, y]) => (
        <circle key={`${x}-${y}`} cx={x} cy={y} r="0.7" fill="#1e3a8a" />
      ))}

      {/* mitochondrion (26,42) */}
      <ellipse cx="26" cy="42" rx="8" ry="4.5" fill="#fca5a5" stroke="#b91c1c" strokeWidth="1" />
      <path d="M 20 42 q 1.5 -2.5 3 0 t 3 0 t 3 0 t 3 0" fill="none" stroke="#b91c1c" strokeWidth="0.7" />

      {/* vacuole (22,56) */}
      <circle cx="22" cy="56" r="6" fill="#bae6fd" stroke="#0284c7" strokeWidth="1" />

      {/* golgi apparatus (26,64): stacked arcs */}
      {[0, 1, 2, 3].map((i) => (
        <path key={i} d={`M 18 ${61 + i * 2.2} q 8 -2.5 16 0`} fill="none" stroke="#059669" strokeWidth="1.1" />
      ))}
      <circle cx="35" cy="60" r="1" fill="#059669" />
      <circle cx="17" cy="69" r="1" fill="#059669" />

      {/* ribosomes (44,72): free cluster */}
      {[[42, 70], [45, 72], [43, 74], [47, 70.5], [46, 74.5], [40, 72.5]].map(([x, y]) => (
        <circle key={`r-${x}-${y}`} cx={x} cy={y} r="0.9" fill="#1e3a8a" />
      ))}

      {/* lysosome (70,28) */}
      <circle cx="70" cy="28" r="4" fill="#f9a8d4" stroke="#be185d" strokeWidth="1" />
      {[[68.5, 27], [71.5, 27.5], [70, 29.5]].map(([x, y]) => (
        <circle key={`l-${x}-${y}`} cx={x} cy={y} r="0.6" fill="#be185d" />
      ))}

      {/* centrioles (38,30): two short perpendicular barrels */}
      <rect x="34" y="28.8" width="6" height="2.4" rx="0.6" fill="#78350f" />
      <rect x="39.5" y="26.5" width="2.4" height="6" rx="0.6" fill="#78350f" />

      {/* cytoplasm target area (52,29) stays empty on purpose */}
    </svg>
  )
}

export default CellDiagram
