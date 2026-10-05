/** Small SVG manipulative: keyboard/touch friendly, no headset or asset download. */
export default function VolumeExplorer({ layers, onChange }: { layers: number; onChange: (value: number) => void }) {
  const cubes = []
  const base = Array.from({ length: 6 }, (_, i) => ({ x: i % 3, y: Math.floor(i / 3) })).sort((a, b) => (a.x+a.y)-(b.x+b.y))
  for (let z = 0; z < layers; z++) for (const { x, y } of base) {
    const cx = 150 + (x-y)*28, cy = 270 + (x+y)*14-z*25
    cubes.push(<g key={`${x}-${y}-${z}`} stroke="#9a3412" strokeWidth="1.3">
      <path d={`M${cx},${cy+28} l28,-14 v25 l-28,14 Z`} fill="#fb923c" />
      <path d={`M${cx-28},${cy+14} l28,14 v25 l-28,-14 Z`} fill="#ea580c" />
      <path d={`M${cx},${cy} l28,14 l-28,14 l-28,-14 Z`} fill="#fed7aa" />
    </g>)
  }
  return <div className="rounded-3xl border border-orange-200 bg-gradient-to-br from-orange-50 via-amber-50 to-white p-5">
    <svg viewBox="60 80 250 290" role="img" aria-label={`Box with 3 by 2 base and ${layers} layers; ${layers*6} unit cubes`} className="mx-auto h-64 w-full max-w-sm">{cubes}</svg>
    <label className="block font-semibold text-orange-950" htmlFor="volume-layers">Stack layers: {layers}</label>
    <input id="volume-layers" aria-label="Number of layers" type="range" min="1" max="6" value={layers} onChange={e => onChange(Number(e.target.value))} className="my-4 w-full accent-orange-600" />
    <div className="grid grid-cols-3 gap-2 text-center text-orange-950">
      <div className="rounded-xl bg-white p-3"><strong>3 × 2</strong><p className="text-xs">Base</p></div>
      <div className="rounded-xl bg-white p-3"><strong>{layers}</strong><p className="text-xs">Layers</p></div>
      <div className="rounded-xl bg-white p-3"><strong>{6*layers}</strong><p className="text-xs">Unit cubes</p></div>
    </div>
  </div>
}
