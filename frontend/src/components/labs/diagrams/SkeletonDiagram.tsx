/**
 * Front-view human skeleton on a 0-100 × 0-100 viewBox. Hotspot coordinates in
 * backend/app/routers/virtual_labs.py SKELETON_IDENTIFY use the same box:
 * skull (50,8) mandible (50,16) clavicle (41,21) sternum (50,31) rib cage (41,36)
 * vertebral column (50,46) humerus (33,34) radius (29,50) ulna (71,50)
 * pelvis (43,55) femur (45,67) patella (44,77) tibia (43,90) fibula (58,89).
 */
const BONE = '#f5efe0'
const EDGE = '#78716c'

export function SkeletonDiagram({ className = '' }: { className?: string }) {
  const bone = { fill: BONE, stroke: EDGE, strokeWidth: 0.9 }
  const line = { stroke: EDGE, strokeWidth: 2.6, strokeLinecap: 'round' as const }
  const thin = { stroke: EDGE, strokeWidth: 1.8, strokeLinecap: 'round' as const }
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet" className={className} role="img" aria-label="Human skeleton diagram">
      {/* skull (50,8) + mandible (50,16) */}
      <circle cx="50" cy="8.5" r="7" {...bone} />
      <circle cx="47.5" cy="8" r="1.3" fill={EDGE} />
      <circle cx="52.5" cy="8" r="1.3" fill={EDGE} />
      <path d="M 45.5 13.5 q 4.5 5 9 0 l -1 3 q -3.5 2.5 -7 0 z" {...bone} />

      {/* vertebral column (50,46) */}
      <line x1="50" y1="17" x2="50" y2="52" {...line} />
      {[19, 22, 25, 28, 31, 34, 37, 40, 43, 46, 49].map((y) => (
        <rect key={y} x="48.3" y={y - 0.7} width="3.4" height="1.4" rx="0.5" fill={BONE} stroke={EDGE} strokeWidth="0.4" />
      ))}

      {/* clavicles (41,21) */}
      <path d="M 37 21 q 6 -1.5 13 0" fill="none" {...thin} />
      <path d="M 50 21 q 7 -1.5 13 0" fill="none" {...thin} />

      {/* sternum (50,31) */}
      <rect x="48.6" y="24" width="2.8" height="14" rx="1.2" {...bone} />

      {/* rib cage (41,36): five arcs each side */}
      {[26, 29, 32, 35, 38].map((y, i) => (
        <g key={y}>
          <path d={`M 49 ${y} q -${8 + i} 0.5 -${9 + i} ${4 + i * 0.4}`} fill="none" {...thin} />
          <path d={`M 51 ${y} q ${8 + i} 0.5 ${9 + i} ${4 + i * 0.4}`} fill="none" {...thin} />
        </g>
      ))}

      {/* humerus (33,34) both arms */}
      <line x1="37" y1="22" x2="31.5" y2="44" {...line} />
      <line x1="63" y1="22" x2="68.5" y2="44" {...line} />

      {/* forearms: radius (29,50) on the left arm, ulna (71,50) on the right */}
      <line x1="31" y1="45" x2="27" y2="58" {...thin} />
      <line x1="33" y1="45" x2="30" y2="58" {...thin} />
      <line x1="69" y1="45" x2="73" y2="58" {...thin} />
      <line x1="67" y1="45" x2="70" y2="58" {...thin} />
      {/* hands */}
      {[-1.5, 0, 1.5].map((dx) => (
        <g key={dx}>
          <line x1={27.5 + dx} y1="59" x2={26 + dx * 1.4} y2="64" stroke={EDGE} strokeWidth="0.8" strokeLinecap="round" />
          <line x1={72.5 + dx} y1="59" x2={74 + dx * 1.4} y2="64" stroke={EDGE} strokeWidth="0.8" strokeLinecap="round" />
        </g>
      ))}

      {/* pelvis (43,55) */}
      <path d="M 40 51 q 10 -3 20 0 l 2 6 q -4 4 -8 2 l -4 -3 l -4 3 q -4 2 -8 -2 z" {...bone} />

      {/* femurs (45,67) */}
      <line x1="46" y1="58" x2="44.5" y2="76" {...line} />
      <line x1="54" y1="58" x2="55.5" y2="76" {...line} />
      {/* patellae (44,77) */}
      <circle cx="44.3" cy="77.2" r="1.6" {...bone} />
      <circle cx="55.7" cy="77.2" r="1.6" {...bone} />
      {/* tibia (43,90) + fibula (58,89) */}
      <line x1="44" y1="79" x2="43" y2="96" {...line} />
      <line x1="56" y1="79" x2="57" y2="96" {...line} />
      <line x1="46.2" y1="79.5" x2="45.8" y2="95" {...thin} />
      <line x1="58.3" y1="79.5" x2="58.7" y2="95" {...thin} />
      {/* feet */}
      <path d="M 41 96.5 h 6" {...thin} fill="none" />
      <path d="M 54 96.5 h 6" {...thin} fill="none" />
    </svg>
  )
}

export default SkeletonDiagram
