/**
 * DeferredThreeD (roadmap R9 low-data mode): wraps ThreeDViewer with a
 * per-browser "Data saver" switch. When on, the lesson shows the text
 * equivalent and a "Load 3D model" button instead of downloading the GLB
 * automatically. The preference is remembered (localStorage si.dataSaver)
 * and also read by other heavy media surfaces.
 */
import { useEffect, useState } from 'react'
import { ThreeDViewer } from './ThreeDViewer'

export function readDataSaver(): boolean {
  try { return localStorage.getItem('si.dataSaver') === '1' } catch { return false }
}
export function writeDataSaver(on: boolean): void {
  try { localStorage.setItem('si.dataSaver', on ? '1' : '0') } catch { /* private mode */ }
}

export function DataSaverToggle({ className = '' }: { className?: string }) {
  const [on, setOn] = useState(readDataSaver())
  useEffect(() => { writeDataSaver(on) }, [on])
  return (
    <label className={`inline-flex items-center gap-2 text-xs text-gray-600 ${className}`} data-testid="data-saver-toggle">
      <input type="checkbox" checked={on} onChange={(e) => { setOn(e.target.checked); window.dispatchEvent(new Event('si:datasaver')) }} />
      Data saver {on ? 'on — heavy media loads on demand' : 'off'}
    </label>
  )
}

export function DeferredThreeD({ modelId, description }: { modelId: number; description?: string }) {
  const [saver, setSaver] = useState(readDataSaver())
  const [load, setLoad] = useState(false)
  useEffect(() => {
    const sync = () => setSaver(readDataSaver())
    window.addEventListener('si:datasaver', sync)
    return () => window.removeEventListener('si:datasaver', sync)
  }, [])
  if (saver && !load) {
    return (
      <div className="glass-panel rounded-xl p-4" data-testid="deferred-3d">
        <p className="text-sm font-semibold text-gray-900">3D model not loaded (data saver is on)</p>
        {description ? <p className="text-sm text-gray-700 mt-1 whitespace-pre-wrap">{description}</p> : <p className="text-xs text-gray-500 mt-1">No text description for this model.</p>}
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button type="button" onClick={() => setLoad(true)} className="si-btn-primary !py-1.5 !text-xs">Load the 3D model</button>
          <DataSaverToggle />
        </div>
      </div>
    )
  }
  return (
    <div>
      <ThreeDViewer modelId={modelId} description={description} />
      <DataSaverToggle className="mt-1" />
    </div>
  )
}

export default DeferredThreeD
