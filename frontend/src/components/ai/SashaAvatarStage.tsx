import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js'

type SashaMood = 'idle' | 'thinking' | 'talking' | 'celebrate'

interface SashaAvatarStageProps {
  mood?: SashaMood
  className?: string
}

export function SashaAvatarStage({ mood = 'idle', className = '' }: SashaAvatarStageProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const moodRef = useRef(mood)
  const [failed, setFailed] = useState(false)

  useEffect(() => { moodRef.current = mood }, [mood])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true })
    } catch {
      setFailed(true)
      return
    }

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100)
    camera.position.set(0, 0.15, 7)
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.35
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8))

    scene.add(new THREE.HemisphereLight(0xdbeafe, 0x111827, 2.2))
    const key = new THREE.DirectionalLight(0xffffff, 3.2)
    key.position.set(4, 7, 6)
    scene.add(key)
    const orange = new THREE.DirectionalLight(0xfb923c, 2.1)
    orange.position.set(-5, 2, 2)
    scene.add(orange)
    const amber = new THREE.PointLight(0xfbbf24, 18, 12)
    amber.position.set(2.5, -1, 2)
    scene.add(amber)

    const platformMaterial = new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.22, side: THREE.DoubleSide })
    const platform = new THREE.Mesh(new THREE.RingGeometry(1.25, 1.35, 72), platformMaterial)
    platform.rotation.x = Math.PI / 2
    platform.position.y = -1.72
    scene.add(platform)

    let model: THREE.Object3D | null = null
    let modelBaseY = 0
    let frame = 0
    let disposed = false
    const loader = new GLTFLoader()
    const draco = new DRACOLoader()
    draco.setDecoderPath('/sasha-tutor/draco/')
    loader.setDRACOLoader(draco)
    loader.load(
      '/sasha-tutor/models/Sasha-Character.draco.glb',
      (gltf) => {
        if (disposed) return
        model = gltf.scene
        const box = new THREE.Box3().setFromObject(model)
        const size = box.getSize(new THREE.Vector3())
        const center = box.getCenter(new THREE.Vector3())
        const scale = 3.35 / Math.max(size.x, size.y, size.z, 1)
        model.scale.setScalar(scale)
        modelBaseY = -center.y * scale - 0.05
        model.position.set(-center.x * scale, modelBaseY, -center.z * scale)
        model.rotation.y = Math.PI
        scene.add(model)
      },
      undefined,
      () => setFailed(true),
    )

    const pointer = new THREE.Vector2()
    const onPointerMove = (event: PointerEvent) => {
      const rect = canvas.getBoundingClientRect()
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
      pointer.y = ((event.clientY - rect.top) / rect.height) * 2 - 1
    }
    canvas.addEventListener('pointermove', onPointerMove)

    const resize = () => {
      const width = canvas.clientWidth || 1
      const height = canvas.clientHeight || 1
      renderer.setSize(width, height, false)
      camera.aspect = width / height
      camera.updateProjectionMatrix()
    }
    const observer = new ResizeObserver(resize)
    observer.observe(canvas)
    resize()

    const startedAt = performance.now()
    const render = (now = performance.now()) => {
      frame = requestAnimationFrame(render)
      const t = (now - startedAt) / 1000
      if (model) {
        const currentMood = moodRef.current
        model.rotation.y += ((Math.PI + pointer.x * 0.14) - model.rotation.y) * 0.035
        model.rotation.x += ((-pointer.y * 0.035) - model.rotation.x) * 0.035
        model.rotation.z = currentMood === 'thinking'
          ? 0.06 + Math.sin(t * 1.2) * 0.025
          : currentMood === 'celebrate' ? Math.sin(t * 7) * 0.045 : Math.sin(t * 0.8) * 0.012
        model.position.y = modelBaseY + Math.sin(t * (currentMood === 'talking' ? 3.2 : 1.35)) * 0.035
      }
      platform.rotation.z = t * 0.08
      platformMaterial.opacity = 0.18 + Math.sin(t * 1.8) * 0.05
      renderer.render(scene, camera)
    }
    render()

    return () => {
      disposed = true
      cancelAnimationFrame(frame)
      observer.disconnect()
      canvas.removeEventListener('pointermove', onPointerMove)
      draco.dispose()
      platform.geometry.dispose()
      platformMaterial.dispose()
      scene.traverse((object) => {
        const mesh = object as THREE.Mesh
        if (mesh.geometry && mesh !== platform) mesh.geometry.dispose()
        const materials = Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : []
        materials.forEach((material) => material.dispose())
      })
      renderer.dispose()
    }
  }, [])

  if (failed) {
    return (
      <div className={`grid place-items-center ${className}`} role="img" aria-label="Sasha AI tutor">
        <div className="grid h-44 w-44 place-items-center rounded-[3rem] border border-orange-300/30 bg-orange-300/10 text-6xl shadow-[0_0_80px_rgba(249,115,22,0.24)]"><span aria-hidden>✦</span></div>
      </div>
    )
  }

  return <canvas ref={canvasRef} className={`h-full w-full touch-none ${className}`} aria-label="Interactive 3D Sasha tutor" />
}

export default SashaAvatarStage
