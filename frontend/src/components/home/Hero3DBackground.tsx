import React, { useEffect } from 'react'

export default function Hero3DBackground() {
  useEffect(() => {
    if (!document.querySelector('script[data-mv]')) {
      const s = document.createElement('script')
      s.type = 'module'
      s.src = 'https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js'
      s.setAttribute('data-mv', 'true')
      document.head.appendChild(s)
    }
  }, [])

  return (
    <div style={{
      position: 'absolute',
      top: '50%',
      left: '50%',
      transform: 'translate(-50%, -50%)',
      width: '75%',
      height: '90%',
      zIndex: 1,
      pointerEvents: 'none',
      opacity: 0.85,
    }}>
      {/* @ts-ignore */}
      <model-viewer
        src="/models/logo.glb"
        auto-rotate
        auto-rotate-delay="0"
        rotation-per-second="25deg"
        interaction-prompt="none"
        shadow-intensity="0"
        exposure="1.0"
        environment-image="neutral"
        style={{
          width: '100%',
          height: '100%',
          background: 'transparent',
          '--progress-bar-color': 'transparent',
        } as React.CSSProperties}
      />
    </div>
  )
}
