/**
 * 3D GLB viewer (Phase 2, teaching-grade): auto-fits ANY model to the
 * viewport regardless of its real-world scale, orbit/zoom/pan, Reset view,
 * and full GPU disposal on unmount. Streams the model through the
 * authenticated API as a blob (never a public URL).
 *
 * WP2 (v2.0 §6) additions, all optional so existing call sites are untouched:
 *   anchors       — markers at NORMALISED bounding-box coordinates (0..1 per
 *                   axis), the storage format of 3D task anchors. Survive the
 *                   auto-fit and any rescale (mesh-relative, never screen).
 *   onAnchorClick — learner picked a marker (match / identify / assemble).
 *   onPickPoint   — instructor clicked the model surface: receives the
 *                   normalised coordinates for the Annotation Placer.
 *   onEvidence    — path events for the §6.3 evidence trail: rotate (throttled),
 *                   zoom, reset.
 *   selectedIds / highlightIds — marker styling.
 */
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { loadGlb } from "./load-glb";
import { createXRSession } from "./xr-session";
import { threeDAPI } from "@/api/threeD";

export interface ViewerAnchor {
  id: string;
  region?: string | null;
  label?: string;
  position: number[];
}

export interface EvidenceEvent {
  type: "rotate" | "zoom" | "reset" | "view";
  t: number;
  [k: string]: string | number | boolean | null | undefined;
}

export interface ThreeDViewerProps {
  sourceUrl?: string;
  sourceBlob?: Blob;
  enableXR?: boolean;
  modelControls?: {
    rotation_y: number;
    scale: number;
    explode: number;
    playing: boolean;
  };
  modelId: number;
  height?: number;
  anchors?: ViewerAnchor[];
  selectedIds?: string[];
  highlightIds?: string[];
  showRegionNames?: boolean;
  onAnchorClick?: (anchorId: string) => void;
  onPickPoint?: (normalized: [number, number, number]) => void;
  onEvidence?: (event: EvidenceEvent) => void;
  /** Text equivalent for screen readers / T5 (v2.0 §10.11) */
  description?: string;
  /** Tier Preview (v2.0 §4.2, WP6): T3 = auto-rotate, non-interactive */
  autoRotate?: boolean;
  interactive?: boolean;
  /** Performance meter: fps + scene triangle count, ~1/s */
  onStats?: (stats: ViewerStats) => void;
  /** Set to a function that returns a PNG data URL of the current frame (T4 still) */
  captureRef?: React.MutableRefObject<(() => string | null) | null>;
}

export interface ViewerStats {
  fps: number;
  triangles: number;
  drawCalls: number;
}

function pickTier(): "T2" | "T3" | undefined {
  try {
    if (localStorage.getItem("si.dataSaver") === "1") return "T3";
  } catch {
    /* private mode */
  }
  const mem = (navigator as any).deviceMemory as number | undefined;
  if ((mem != null && mem <= 4) || window.innerWidth < 768) return "T2";
  return undefined;
}

function markerTexture(fill: string, text: string): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = 128;
  c.height = 128;
  const ctx = c.getContext("2d")!;
  ctx.beginPath();
  ctx.arc(64, 64, 52, 0, Math.PI * 2);
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.lineWidth = 8;
  ctx.strokeStyle = "#ffffff";
  ctx.stroke();
  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 56px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 64, 66);
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}

export function ThreeDViewer({
  modelId,
  sourceUrl,
  sourceBlob,
  enableXR = false,
  modelControls,
  height = 480,
  anchors = [],
  selectedIds = [],
  highlightIds = [],
  showRegionNames = true,
  onAnchorClick,
  onPickPoint,
  onEvidence,
  description,
  autoRotate = false,
  interactive = true,
  onStats,
  captureRef,
}: ThreeDViewerProps) {
  const optsRef = useRef({ autoRotate, interactive, onStats, modelControls });
  optsRef.current = { autoRotate, interactive, onStats, modelControls };
  const mountRef = useRef<HTMLDivElement>(null);
  const fitRef = useRef<(() => void) | null>(null);
  const sceneRef = useRef<{
    box: THREE.Box3;
    size: THREE.Vector3;
    model: THREE.Object3D;
    markers: THREE.Group;
    scene: THREE.Scene;
    camera: THREE.Camera;
  } | null>(null);
  const callbacks = useRef({ onAnchorClick, onPickPoint, onEvidence });
  callbacks.current = { onAnchorClick, onPickPoint, onEvidence };
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const [showText, setShowText] = useState(false);
  const [xrMessage, setXRMessage] = useState("Checking AR / VR support�");
  const [xrActive, setXRActive] = useState(false);
  const [xrSupport, setXRSupport] = useState({ ar: false, vr: false });
  const xrToggle = useRef<
    ((mode: "immersive-ar" | "immersive-vr") => Promise<void>) | null
  >(null);
  useEffect(() => {
    let live = true;
    const xr = (navigator as any).xr;
    if (!enableXR) return;
    if (!xr || !window.isSecureContext) {
      setXRMessage(
        "AR / VR needs HTTPS and a supported device. Screen controls remain available.",
      );
      return;
    }
    Promise.all([
      xr.isSessionSupported("immersive-ar"),
      xr.isSessionSupported("immersive-vr"),
    ])
      .then(([ar, vr]) => {
        if (live) {
          setXRSupport({ ar, vr });
          setXRMessage(
            ar || vr
              ? "AR / VR available on this device."
              : "No XR device detected. Use the screen controls.",
          );
        }
      })
      .catch(() => {
        if (live) setXRMessage("XR capability check failed. Use screen mode.");
      });
    return () => {
      live = false;
    };
  }, [enableXR]);
  const [ready, setReady] = useState(0);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    setLoading(true);
    setError(null);
    setProgress(0);

    let disposed = false;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf6f7f9);
    const camera = new THREE.PerspectiveCamera(
      45,
      mount.clientWidth / height,
      0.01,
      5000,
    );
    camera.position.set(0, 1.5, 5);
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        preserveDrawingBuffer: true,
        alpha: true,
      });
    } catch {
      setError(
        "3D graphics are unavailable. Use the text descriptions and accessible controls.",
      );
      setLoading(false);
      return;
    }
    renderer.setSize(mount.clientWidth, height);
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    // WP8 §10.11: keyboard equivalents — arrows orbit, +/- zoom, R resets
    const onKey = (e: KeyboardEvent) => {
      const step = 0.15;
      const sph = new THREE.Spherical().setFromVector3(
        camera.position.clone().sub(controls.target),
      );
      if (e.key === "ArrowLeft") sph.theta -= step;
      else if (e.key === "ArrowRight") sph.theta += step;
      else if (e.key === "ArrowUp") sph.phi = Math.max(0.05, sph.phi - step);
      else if (e.key === "ArrowDown")
        sph.phi = Math.min(Math.PI - 0.05, sph.phi + step);
      else if (e.key === "+" || e.key === "=") sph.radius *= 0.85;
      else if (e.key === "-" || e.key === "_") sph.radius *= 1.15;
      else if (e.key === "r" || e.key === "R") {
        fitRef.current?.();
        e.preventDefault();
        return;
      } else return;
      e.preventDefault();
      camera.position
        .copy(controls.target)
        .add(new THREE.Vector3().setFromSpherical(sph));
      controls.update();
      callbacks.current.onEvidence?.({ type: "rotate", t: Date.now() });
    };
    mount.addEventListener("keydown", onKey);
    let lastRotateEvidence = 0;
    controls.addEventListener("change", () => {
      const now = Date.now();
      if (now - lastRotateEvidence > 600) {
        lastRotateEvidence = now;
        callbacks.current.onEvidence?.({ type: "rotate", t: now });
      }
    });

    scene.add(new THREE.AmbientLight(0xffffff, 0.7));
    const key = new THREE.DirectionalLight(0xffffff, 1.2);
    key.position.set(3, 5, 4);
    scene.add(key);
    const grid = new THREE.GridHelper(10, 20, 0xcccccc, 0xeeeeee);
    scene.add(grid);
    const markers = new THREE.Group();
    const contentRoot = new THREE.Group();
    scene.add(contentRoot);
    contentRoot.add(markers);
    const xr = enableXR
      ? createXRSession(
          renderer,
          scene,
          camera,
          contentRoot,
          setXRMessage,
          setXRActive,
          (id) => callbacks.current.onAnchorClick?.(id),
        )
      : null;
    xrToggle.current = xr?.toggle || null;
    let mixer: THREE.AnimationMixer | null = null;
    let lastTime = performance.now();
    let controlGroup: THREE.Group | null = null;
    const parts: {
      obj: THREE.Object3D;
      position: THREE.Vector3;
      offset: THREE.Vector3;
    }[] = [];

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let downAt: { x: number; y: number } | null = null;

    const onPointerDown = (e: PointerEvent) => {
      downAt = { x: e.clientX, y: e.clientY };
    };
    const onPointerUp = (e: PointerEvent) => {
      if (!downAt || !sceneRef.current) return;
      const moved = Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y);
      downAt = null;
      if (moved > 6) return; // it was a drag, not a click
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const { box, size, model } = sceneRef.current;
      const hitMarkers = raycaster.intersectObjects(markers.children, false);
      if (hitMarkers.length > 0) {
        const id = (hitMarkers[0].object as THREE.Sprite).userData
          .anchorId as string;
        callbacks.current.onAnchorClick?.(id);
        return;
      }
      const hits = raycaster.intersectObject(model, true);
      if (hits.length > 0 && callbacks.current.onPickPoint) {
        const p = hits[0].point;
        const n: [number, number, number] = [
          Math.min(1, Math.max(0, (p.x - box.min.x) / (size.x || 1))),
          Math.min(1, Math.max(0, (p.y - box.min.y) / (size.y || 1))),
          Math.min(1, Math.max(0, (p.z - box.min.z) / (size.z || 1))),
        ];
        callbacks.current.onPickPoint(n);
      }
    };
    const onWheel = () =>
      callbacks.current.onEvidence?.({ type: "zoom", t: Date.now() });
    renderer.domElement.addEventListener("pointerdown", onPointerDown);
    renderer.domElement.addEventListener("pointerup", onPointerUp);
    renderer.domElement.addEventListener("wheel", onWheel, { passive: true });
    (sourceBlob
      ? sourceBlob.arrayBuffer()
      : sourceUrl
        ? fetch(sourceUrl).then(response => {
            if (!response.ok) throw new Error('Model download failed');
            return response.arrayBuffer();
          })
        : threeDAPI.downloadBytes(modelId, pickTier(), percent => { if (!disposed) setProgress(percent); })
    )
      .then(data => { if (!disposed) return loadGlb(data); })
      .then((gltf) => {
            if (disposed || !gltf) return;
            const model = gltf.scene;
            controlGroup = new THREE.Group();
            contentRoot.add(controlGroup);
            controlGroup.add(model);
            if (gltf.animations.length) {
              mixer = new THREE.AnimationMixer(model);
              gltf.animations.forEach((clip) => mixer!.clipAction(clip).play());
            }

            // Auto-fit: center at origin and frame ANY model (mm-scale or
            // km-scale) so it fills the viewport. This is what makes the
            // viewer teaching-grade — instructors never tune cameras.
            const box0 = new THREE.Box3().setFromObject(model);
            const sizeLen = box0.getSize(new THREE.Vector3()).length() || 1;
            const center = box0.getCenter(new THREE.Vector3());
            model.position.sub(center);
            model.updateMatrixWorld(true);
            const box = new THREE.Box3().setFromObject(model); // post-centering box for anchors
            const size = box.getSize(new THREE.Vector3());
            const dist =
              (sizeLen / (2 * Math.tan((camera.fov * Math.PI) / 360))) * 1.4;
            camera.near = sizeLen / 1000;
            camera.far = sizeLen * 100;
            camera.updateProjectionMatrix();
            controls.maxDistance = sizeLen * 10;
            const reset = () => {
              camera.position.set(dist * 0.5, dist * 0.4, dist);
              controls.target.set(0, 0, 0);
              controls.update();
            };
            fitRef.current = () => {
              reset();
              callbacks.current.onEvidence?.({ type: "reset", t: Date.now() });
            };
            reset();
            controlGroup.add(markers);
            model.traverse((obj) => {
              if ((obj as THREE.Mesh).isMesh) {
                const world = new THREE.Box3()
                  .setFromObject(obj)
                  .getCenter(new THREE.Vector3());
                const local = obj.parent?.worldToLocal(world.clone()) || world;
                parts.push({
                  obj,
                  position: obj.position.clone(),
                  offset: local.normalize().multiplyScalar(sizeLen * 0.2),
                });
              }
            });
            sceneRef.current = { box, size, model, markers, scene, camera };
            setLoading(false);
            setReady((r) => r + 1);
      })
      .catch((error: unknown) => {
        if (!disposed) {
          setError(error instanceof Error ? error.message : "Could not load the 3D model. Check the model file and retry.");
          setLoading(false);
        }
      });

    let frames = 0;
    let statsAt = performance.now();
    const animate = (_time?: number, frame?: any) => {
      if (disposed) return;
      xr?.frame(frame);
      const tick = performance.now();
      const delta = Math.min((tick - lastTime) / 1000, 0.1);
      lastTime = tick;
      const values = optsRef.current.modelControls;
      if (values && controlGroup) {
        controlGroup.rotation.y = THREE.MathUtils.degToRad(values.rotation_y);
        controlGroup.scale.setScalar(values.scale);
        parts.forEach((p) =>
          p.obj.position
            .copy(p.position)
            .addScaledVector(p.offset, values.explode),
        );
        if (values.playing) mixer?.update(delta);
      }
      controls.autoRotate = optsRef.current.autoRotate;
      controls.autoRotateSpeed = 1.5;
      controls.enabled =
        optsRef.current.interactive && !renderer.xr.isPresenting;
      controls.update();
      renderer.render(scene, camera);
      frames += 1;
      const now = performance.now();
      if (now - statsAt >= 1000) {
        optsRef.current.onStats?.({
          fps: Math.round((frames * 1000) / (now - statsAt)),
          triangles: renderer.info.render.triangles,
          drawCalls: renderer.info.render.calls,
        });
        frames = 0;
        statsAt = now;
      }
    };
    renderer.setAnimationLoop(animate);
    if (captureRef)
      captureRef.current = () => {
        try {
          renderer.render(scene, camera);
          return renderer.domElement.toDataURL("image/png");
        } catch {
          return null;
        }
      };

    const onResize = () => {
      if (!mount.clientWidth) return;
      camera.aspect = mount.clientWidth / height;
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, height);
    };
    window.addEventListener("resize", onResize);
    const resizeObserver = new ResizeObserver(onResize);
    resizeObserver.observe(mount);

    return () => {
      disposed = true;
      renderer.setAnimationLoop(null);
      xr?.dispose();
      xrToggle.current = null;
      mixer?.stopAllAction();
      if (captureRef) captureRef.current = null;
      window.removeEventListener("resize", onResize);
      resizeObserver.disconnect();
      mount.removeEventListener("keydown", onKey);
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointerup", onPointerUp);
      renderer.domElement.removeEventListener("wheel", onWheel);
      controls.dispose();
      sceneRef.current = null;
      scene.traverse((obj) => {
        const mesh = obj as THREE.Mesh;
        if (mesh.geometry) mesh.geometry.dispose();
        const mat = mesh.material as
          | THREE.Material
          | THREE.Material[]
          | undefined;
        const materials = Array.isArray(mat) ? mat : mat ? [mat] : [];
        materials.forEach((m) => {
          Object.values(m).forEach((value) => {
            if (value instanceof THREE.Texture) value.dispose();
          });
          m.dispose();
        });
      });
      renderer.dispose();
      if (renderer.domElement.parentNode === mount)
        mount.removeChild(renderer.domElement);
    };
  }, [modelId, height, captureRef, sourceUrl, sourceBlob, enableXR]);

  // Rebuild markers whenever anchors / selection change (after the model is ready).
  useEffect(() => {
    const ctx = sceneRef.current;
    if (!ctx) return;
    const { box, size, markers } = ctx;
    while (markers.children.length) {
      const s = markers.children[0] as THREE.Sprite;
      markers.remove(s);
      (s.material as THREE.SpriteMaterial).map?.dispose();
      s.material.dispose();
    }
    const scale = Math.max(size.x, size.y, size.z) * 0.06 || 0.1;
    anchors.forEach((a, i) => {
      const selected = selectedIds.includes(a.id);
      const highlighted = highlightIds.includes(a.id);
      const fill = selected ? "#059669" : highlighted ? "#f59e0b" : "#2563eb";
      const text = showRegionNames ? String(i + 1) : "";
      const mat = new THREE.SpriteMaterial({
        map: markerTexture(fill, text),
        depthTest: false,
        transparent: true,
      });
      const sprite = new THREE.Sprite(mat);
      sprite.position.set(
        box.min.x + (a.position[0] ?? 0.5) * size.x,
        box.min.y + (a.position[1] ?? 0.5) * size.y,
        box.min.z + (a.position[2] ?? 0.5) * size.z,
      );
      sprite.scale.set(scale, scale, 1);
      sprite.renderOrder = 999;
      sprite.userData.anchorId = a.id;
      markers.add(sprite);
    });
  }, [anchors, selectedIds, highlightIds, showRegionNames, ready]);

  return (
    <div className="relative">
      {enableXR && (
        <div className="space-y-2 mb-3">
          <div className="sf-actions">
            <button
              type="button"
              className="sf-secondary"
              disabled={loading || !!error || (!xrActive && !xrSupport.ar)}
              onClick={() => void xrToggle.current?.("immersive-ar")}
            >
              {xrActive ? "Exit XR" : "Place in AR"}
            </button>
            <button
              type="button"
              className="sf-secondary"
              disabled={loading || !!error || (!xrActive && !xrSupport.vr)}
              onClick={() => void xrToggle.current?.("immersive-vr")}
            >
              {xrActive ? "Exit XR" : "Enter VR"}
            </button>
          </div>
          <p role="status" className="sf-muted">
            {xrMessage}
          </p>
        </div>
      )}
      {error && (
        <div
          role="alert"
          className="p-4 border border-amber-200 bg-amber-50 rounded-lg text-sm text-amber-800 mb-2"
        >
          {error}
        </div>
      )}
      <div
        ref={mountRef}
        style={{ height }}
        className="rounded-xl overflow-hidden border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-400"
        role="img"
        tabIndex={0}
        aria-label={
          description
            ? `3D model: ${description}. Use arrow keys to rotate, plus and minus to zoom, R to reset.`
            : "3D model viewer. Use arrow keys to rotate, plus and minus to zoom, R to reset."
        }
      />
      {loading && !error && (
        <div className="absolute inset-0 grid place-items-center pointer-events-none">
          <span className="text-sm text-gray-500 bg-white/80 px-3 py-1 rounded-full">
            Loading 3D model…{progress > 0 ? ` ${progress}%` : ""}
          </span>
        </div>
      )}
      {!error && !loading && (
        <button
          type="button"
          onClick={() => fitRef.current?.()}
          className="absolute top-2 right-2 px-3 py-1 text-xs font-medium bg-white/90 border border-gray-300 rounded-full hover:bg-white"
        >
          Reset view
        </button>
      )}
      <p className="text-[11px] text-gray-400 mt-1">
        Drag to rotate · scroll to zoom · right-drag to pan · keyboard: arrows /
        + − / R
        {anchors.length > 0 ? " · click a numbered marker to select it" : ""}
        {onPickPoint ? " · click the surface to place an anchor" : ""}
        {description && (
          <button
            type="button"
            onClick={() => setShowText((v) => !v)}
            className="ml-2 underline text-gray-500"
            aria-expanded={showText}
          >
            {showText ? "Hide text equivalent" : "Text equivalent"}
          </button>
        )}
      </p>
      {description &&
        (showText ? (
          <p
            className="mt-1 text-sm text-gray-700 rounded-lg bg-gray-50 border border-gray-200 p-2"
            data-testid="text-equivalent"
          >
            {description}
          </p>
        ) : (
          <p className="sr-only">{description}</p>
        ))}
    </div>
  );
}

export default ThreeDViewer;
