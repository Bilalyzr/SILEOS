import * as THREE from "three";
import { loadGlb } from "@/components/three-d/load-glb";

export interface TowerSceneOptions {
  quality?: "low" | "medium" | "high";
  reducedMotion?: boolean;
  layout?: "split" | "center";
  onError?: (err: unknown) => void;
}

class RoomEnvironment extends THREE.Scene {
  constructor() {
    super();
    this.name = "RoomEnvironment";
    this.position.y = -3.5;

    const boxGeo = new THREE.BoxGeometry();
    boxGeo.deleteAttribute("uv");

    const roomMat = new THREE.MeshStandardMaterial({ side: THREE.BackSide });
    const boxMat = new THREE.MeshStandardMaterial();

    const mainLight = new THREE.PointLight(0xffffff, 900, 28, 2);
    mainLight.position.set(0.418, 16.199, 0.3);
    this.add(mainLight);

    const room = new THREE.Mesh(boxGeo, roomMat);
    room.position.set(-0.757, 13.219, 0.717);
    room.scale.set(31.713, 28.305, 28.591);
    this.add(room);

    const boxes = new THREE.InstancedMesh(boxGeo, boxMat, 6);
    const dummy = new THREE.Object3D();

    dummy.position.set(-10.906, 2.009, 1.846);
    dummy.rotation.set(0, -0.195, 0);
    dummy.scale.set(2.328, 7.905, 4.651);
    dummy.updateMatrix();
    boxes.setMatrixAt(0, dummy.matrix);

    dummy.position.set(-5.607, -0.754, -0.758);
    dummy.rotation.set(0, 0.994, 0);
    dummy.scale.set(1.97, 1.534, 3.955);
    dummy.updateMatrix();
    boxes.setMatrixAt(1, dummy.matrix);

    dummy.position.set(6.167, 0.857, 7.803);
    dummy.rotation.set(0, 0.561, 0);
    dummy.scale.set(3.927, 6.285, 3.687);
    dummy.updateMatrix();
    boxes.setMatrixAt(2, dummy.matrix);

    dummy.position.set(-2.017, 0.018, 6.124);
    dummy.rotation.set(0, 0.333, 0);
    dummy.scale.set(2.002, 4.566, 2.064);
    dummy.updateMatrix();
    boxes.setMatrixAt(3, dummy.matrix);

    dummy.position.set(2.291, -0.756, -2.621);
    dummy.rotation.set(0, -0.286, 0);
    dummy.scale.set(1.546, 1.552, 1.496);
    dummy.updateMatrix();
    boxes.setMatrixAt(4, dummy.matrix);

    dummy.position.set(-2.193, -0.369, -5.547);
    dummy.rotation.set(0, 0.516, 0);
    dummy.scale.set(3.875, 3.487, 2.986);
    dummy.updateMatrix();
    boxes.setMatrixAt(5, dummy.matrix);

    this.add(boxes);

    const emissiveMat = (intensity: number) =>
      new THREE.MeshLambertMaterial({
        color: 0x000000,
        emissive: 0xffffff,
        emissiveIntensity: intensity,
      });

    const light1 = new THREE.Mesh(boxGeo, emissiveMat(50));
    light1.position.set(-16.116, 14.37, 8.208);
    light1.scale.set(0.1, 2.428, 2.739);
    this.add(light1);

    const light2 = new THREE.Mesh(boxGeo, emissiveMat(50));
    light2.position.set(-16.109, 18.021, -8.207);
    light2.scale.set(0.1, 2.425, 2.751);
    this.add(light2);

    const light3 = new THREE.Mesh(boxGeo, emissiveMat(17));
    light3.position.set(14.904, 12.198, -1.832);
    light3.scale.set(0.15, 4.265, 6.331);
    this.add(light3);

    const light4 = new THREE.Mesh(boxGeo, emissiveMat(43));
    light4.position.set(-0.462, 8.89, 14.52);
    light4.scale.set(4.38, 5.441, 0.088);
    this.add(light4);

    const light5 = new THREE.Mesh(boxGeo, emissiveMat(20));
    light5.position.set(3.235, 11.486, -12.541);
    light5.scale.set(2.5, 2, 0.1);
    this.add(light5);

    const light6 = new THREE.Mesh(boxGeo, emissiveMat(100));
    light6.position.set(0, 20, 0);
    light6.scale.set(1, 0.1, 1);
    this.add(light6);
  }

  dispose() {
    const resources = new Set<{ dispose: () => void }>();
    this.traverse((obj: any) => {
      if (obj.isMesh) {
        if (obj.geometry) resources.add(obj.geometry);
        if (obj.material) resources.add(obj.material);
      }
    });
    for (const res of resources) {
      res.dispose();
    }
  }
}

export const STAGE_RANGES: Record<string, [number, number]> = {
  design: [0.06, 0.22],
  approvals: [0.22, 0.38],
  foundation: [0.22, 0.36],
  structure: [0.38, 0.56],
  envelope: [0.56, 0.72],
  finishes: [0.72, 0.88],
  handover: [0.88, 1],
};

const COPPER_COLOR = new THREE.Color("#ff9b54");

// Hero headset: Meta Quest 3S (from github.com/CourseDesignUK/Quest3s, with
// stray controller fragments stripped). Its faceplate already faces +Z, so
// rotation stays zero; span is its longest side (front to back) in scene
// units; explode is how far parts drift apart in the hero, as a share of
// that span.
const HEADSET_MODEL = {
  url: "/models/ar/meta-quest-3s.glb",
  hideNodes: [] as string[],
  rotation: [0, 0, 0] as [number, number, number],
  span: 10.4,
  explode: 0.16,
};

// Physically based finishes for the headset, keyed by the GLB's material
// names (the file ships with flat placeholder colours).
const HEADSET_FINISH: Record<string, THREE.MeshPhysicalMaterialParameters> = {
  // Front shell: satin white polycarbonate under a light clear coat
  Icosphere__0: {
    color: "#efefeb",
    roughness: 0.36,
    clearcoat: 0.45,
    clearcoatRoughness: 0.28,
  },
  // Side arms and top strap: matte textured plastic
  "Quest_Mat.004": { color: "#e4e4e0", roughness: 0.62 },
  "Quest_Mat.005": { color: "#e8e8e4", roughness: 0.58 },
  // Camera clusters and inner housing: glossy black
  "Quest_Mat.002": {
    color: "#151618",
    roughness: 0.4,
    clearcoat: 0.6,
    clearcoatRoughness: 0.18,
  },
  // Facial interface: soft dark fabric
  "Material.004": { color: "#1f2023", roughness: 0.95 },
  // Buttons
  "Material.002": { color: "#121314", roughness: 0.35 },
  // Pancake lenses: coated glass with a faint green reflection
  "Material.001": {
    color: "#0c1411",
    roughness: 0.05,
    metalness: 0.1,
    clearcoat: 1,
    emissive: "#06261a",
    emissiveIntensity: 0.5,
  },
};

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const rangeProgress = (v: number, [a, b]: [number, number]) =>
  clamp01((v - a) / (b - a));
const easeOutCubic = (v: number) => 1 - (1 - v) ** 3;
const easeInOutCubic = (v: number) =>
  v < 0.5 ? 4 * v * v * v : 1 - (-2 * v + 2) ** 3 / 2;
const smoothstep01 = (v: number) => v * v * (3 - 2 * v);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

const MOOD_KEYFRAMES = [
  {
    at: 0,
    top: "#160b05",
    horizon: "#3b1d0d",
    sun: "#ffd5a5",
    sunI: 1.5,
    hemi: 0.5,
    elev: 0.85,
    az: -0.55,
    glow: 0.28,
    exposure: 1.08,
  },
  {
    at: 0.22,
    top: "#1c0e06",
    horizon: "#542912",
    sun: "#ffe4c8",
    sunI: 2.6,
    hemi: 0.6,
    elev: 0.72,
    az: -0.78,
    glow: 0.45,
    exposure: 1.1,
  },
  {
    at: 0.52,
    top: "#241208",
    horizon: "#6e3618",
    sun: "#fff0dc",
    sunI: 3.1,
    hemi: 0.68,
    elev: 0.88,
    az: -0.95,
    glow: 0.55,
    exposure: 1.12,
  },
  {
    at: 0.8,
    top: "#211007",
    horizon: "#9a4516",
    sun: "#ffb875",
    sunI: 3.0,
    hemi: 0.65,
    elev: 0.42,
    az: -1.25,
    glow: 0.9,
    exposure: 1.16,
  },
  {
    at: 1,
    top: "#170b05",
    horizon: "#7a3210",
    sun: "#ff9b54",
    sunI: 2.5,
    hemi: 0.6,
    elev: 0.24,
    az: -1.15,
    glow: 1,
    exposure: 1.2,
  },
].map((m) => ({
  ...m,
  topC: new THREE.Color(m.top),
  horizonC: new THREE.Color(m.horizon),
  sunC: new THREE.Color(m.sun),
}));

function makeCanvas(w: number, h: number) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  return { c, g: c.getContext("2d")! };
}

interface BatchItem {
  x: number;
  y: number;
  z: number;
  sx: number;
  sy: number;
  sz: number;
  t0: number;
  t1?: number;
  ry?: number;
  rx?: number;
  rz?: number;
  q?: THREE.Quaternion;
  color?: string | THREE.Color;
  fromY?: number;
}

class AnimatedBatch {
  geometry: THREE.BufferGeometry;
  material: THREE.Material;
  grow: "y" | "xyz" | "fly" | "none";
  dur: number;
  shadows: { cast: boolean; receive: boolean };
  items: BatchItem[] = [];
  mesh!: THREE.InstancedMesh;
  shown!: Float32Array;
  dummy = new THREE.Object3D();

  constructor(
    geometry: THREE.BufferGeometry,
    material: THREE.Material,
    grow: "y" | "xyz" | "fly" | "none",
    dur: number,
    shadows = { cast: true, receive: true }
  ) {
    this.geometry = geometry;
    this.material = material;
    this.grow = grow;
    this.dur = dur;
    this.shadows = shadows;
  }

  add(item: BatchItem) {
    this.items.push(item);
  }

  build(scene: THREE.Object3D) {
    const count = this.items.length;
    this.mesh = new THREE.InstancedMesh(
      this.geometry,
      this.material,
      Math.max(1, count)
    );
    this.mesh.count = count;
    this.mesh.frustumCulled = false;
    this.mesh.castShadow = this.shadows.cast;
    this.mesh.receiveShadow = this.shadows.receive;
    const col = new THREE.Color();
    this.items.forEach((it, idx) => {
      if (it.color) {
        this.mesh.setColorAt(idx, col.set(it.color as any));
      }
    });
    this.shown = new Float32Array(count).fill(-1);
    scene.add(this.mesh);
    this.update(0);
  }

  amount(item: BatchItem, t: number) {
    const instant = this.grow === "none";
    const enter = instant
      ? +(t >= item.t0)
      : easeOutCubic(clamp01((t - item.t0) / this.dur));
    if (enter <= 0 || item.t1 === undefined) return enter;
    const exit = instant
      ? +(t >= item.t1)
      : smoothstep01(clamp01((t - item.t1) / this.dur));
    return enter * (1 - exit);
  }

  update(t: number) {
    const d = this.dummy;
    let changed = false;
    for (let i = 0; i < this.items.length; i++) {
      const it = this.items[i];
      const amt = this.amount(it, t);
      if (Math.abs(amt - this.shown[i]) < 1e-4) continue;
      this.shown[i] = amt;
      changed = true;
      if (it.q) {
        d.quaternion.copy(it.q);
      } else {
        d.rotation.set(it.rx ?? 0, it.ry ?? 0, it.rz ?? 0);
      }
      if (amt <= 0.001) {
        d.position.set(it.x, it.y, it.z);
        d.scale.set(0, 0, 0);
      } else if (this.grow === "y") {
        const sy = it.sy * amt;
        d.position.set(it.x, it.y - (it.sy - sy) / 2, it.z);
        d.scale.set(it.sx, sy, it.sz);
      } else if (this.grow === "fly") {
        const offsetY = (it.fromY ?? 2.2) * (1 - amt);
        d.position.set(it.x, it.y + offsetY, it.z);
        d.scale.set(it.sx * amt, it.sy * amt, it.sz * amt);
      } else {
        d.position.set(it.x, it.y, it.z);
        d.scale.set(it.sx * amt, it.sy * amt, it.sz * amt);
      }
      d.updateMatrix();
      this.mesh.setMatrixAt(i, d.matrix);
    }
    if (changed) {
      this.mesh.instanceMatrix.needsUpdate = true;
    }
    return changed;
  }
}

class CriticallyDampedSpring {
  x: number;
  stiffness: number;
  v = 0;

  constructor(initial: number, stiffness: number) {
    this.x = initial;
    this.stiffness = stiffness;
  }

  step(target: number, dt: number) {
    const k = this.stiffness;
    const damp = 2 * Math.sqrt(k);
    for (let rem = dt; rem > 0; rem -= 1 / 120) {
      const stepDt = Math.min(rem, 1 / 120);
      this.v += (k * (target - this.x) - damp * this.v) * stepDt;
      this.x += this.v * stepDt;
    }
    if (Math.abs(target - this.x) < 1e-4 && Math.abs(this.v) < 1e-4) {
      this.x = target;
      this.v = 0;
      return false;
    }
    return true;
  }
}

const vec3 = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

/**
 * SashaInfinity Meiporul 3D AR/VR Spatial Learning Glass & Knowledge Studio Scene
 * Uses the exact Sympho Build scroll-driven progressive assembly engine.
 */
export class TowerScene {
  canvas: HTMLCanvasElement;
  opts: Required<Omit<TowerSceneOptions, "onError">> & {
    onError?: (err: unknown) => void;
  };
  renderer!: THREE.WebGLRenderer;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(30, 1, 0.5, 900);
  raf = 0;
  last = 0;
  clock = 0;
  frameNo = 0;
  perfSlow = 0;
  perfN = 0;
  lowPower = false;
  dpr = 1;
  maxDpr = 1;
  visible = true;
  warmed = false;
  warm: Promise<void> = Promise.resolve();
  disposed = false;
  width = 1;
  height = 1;

  target = { hero: 0, build: 0, px: 0, py: 0 };
  springs = {
    hero: new CriticallyDampedSpring(0, 22),
    build: new CriticallyDampedSpring(0, 20),
    px: new CriticallyDampedSpring(0, 7),
    py: new CriticallyDampedSpring(0, 7),
  };

  intro = 0;
  high = true;
  corners: THREE.Vector3[] = [];
  center = new THREE.Vector3(0, 4.4, 0);

  // Wireframe & CAD lines
  lines!: THREE.LineSegments;
  lineVertexCount = 0;
  lineMat = new THREE.LineBasicMaterial({
    color: COPPER_COLOR,
    transparent: true,
    opacity: 0.95,
  });
  boundaryMat = new THREE.LineDashedMaterial({
    color: COPPER_COLOR,
    dashSize: 0.7,
    gapSize: 0.45,
    transparent: true,
    opacity: 0,
  });
  frustumMat = new THREE.LineBasicMaterial({
    color: "#e89b6c",
    transparent: true,
    opacity: 0,
  });

  envTex!: THREE.Texture;
  glowMat!: THREE.MeshBasicMaterial;
  litMat = new THREE.MeshBasicMaterial({
    color: "#ffc98a",
    toneMapped: false,
  });
  cyanGlowMat = new THREE.MeshBasicMaterial({
    color: "#7dd3fc",
    toneMapped: false,
  });
  lampMat = new THREE.MeshBasicMaterial({
    color: "#ffd9a0",
    toneMapped: false,
  });
  beaconMat = new THREE.MeshBasicMaterial({
    color: "#ff5a36",
    toneMapped: false,
  });
  skyMat!: THREE.ShaderMaterial;
  fog!: THREE.Fog;
  sun = new THREE.DirectionalLight("#ffffff", 3);
  hemi = new THREE.HemisphereLight("#dfe6ea", "#2a2622", 0.55);

  mood = {
    top: new THREE.Color(),
    horizon: new THREE.Color(),
    sun: new THREE.Color(),
    sunI: 0,
    hemi: 0,
    elev: 0,
    az: 0,
    glow: 0,
    exposure: 1,
  };

  // Articulated 3D groups for the AR/VR Learning Glass & Spatial Rig
  rigRoot = new THREE.Group();

  // Real 3D GLB AR/VR Headset & Real Meiporul AR Mathematical Model
  realHeadsetRoot = new THREE.Group();
  realHeadsetLoaded = false;
  contactShadow!: THREE.Mesh;
  realSubAssemblies: {
    node: THREE.Object3D;
    basePos: THREE.Vector3;
    explodeOffset: THREE.Vector3;
    t0: number;
    t1: number;
  }[] = [];

  // Holographic Learning Suite (Stage 04 & 05)
  holoGroup = new THREE.Group();
  holoCore = new THREE.Group();
  helixGroup = new THREE.Group();
  hudScreensGroup = new THREE.Group();
  gyroRing1 = new THREE.Group();
  gyroRing2 = new THREE.Group();
  gyroRing3 = new THREE.Group();
  beamLeft!: THREE.Mesh;
  beamRight!: THREE.Mesh;
  beamMat!: THREE.MeshBasicMaterial;

  // Precision Optical Calibration Gantries (Stage 02 & 03)
  leftGantry = new THREE.Group();
  leftGantryArm = new THREE.Group();
  rightGantry = new THREE.Group();
  rightGantryArm = new THREE.Group();

  dust?: THREE.Points;
  dustSeeds = new Float32Array(0);
  batches: AnimatedBatch[] = [];
  geometries: THREE.BufferGeometry[] = [];
  materials: THREE.Material[] = [];
  textures: THREE.Texture[] = [];
  unit!: THREE.BoxGeometry;

  tmp = {
    right: new THREE.Vector3(),
    up: new THREE.Vector3(),
    back: new THREE.Vector3(),
    v: new THREE.Vector3(),
  };

  constructor(canvas: HTMLCanvasElement, opts: TowerSceneOptions = {}) {
    this.canvas = canvas;
    const defaultLayout =
      typeof window !== "undefined" && window.innerWidth >= 1024
        ? "split"
        : "center";
    this.opts = {
      quality: opts.quality ?? "high",
      reducedMotion: Boolean(opts.reducedMotion),
      layout: opts.layout ?? defaultLayout,
      onError: opts.onError,
    };
    this.high = this.opts.quality !== "low";

    try {
      this.renderer = new THREE.WebGLRenderer({
        canvas,
        // MSAA is cheap on current integrated GPUs; without it the white
        // headset edges shimmer and step. Only the low tier goes without.
        antialias: this.opts.quality !== "low",
        alpha: false,
        powerPreference: "high-performance",
      });
    } catch (err) {
      this.disposed = true;
      this.opts.onError?.(err);
      return;
    }

    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.08;
    // Render at the screen's real density (Retina / HiDPI laptops are 2x);
    // the old 1.25-1.6 caps made the scene visibly soft.
    this.maxDpr = Math.min(
      typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1,
      this.opts.quality === "low" ? 1.25 : 2
    );
    this.dpr = this.maxDpr;
    this.renderer.setPixelRatio(this.dpr);
    this.renderer.shadowMap.enabled = this.high;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.renderer.shadowMap.autoUpdate = false;

    canvas.addEventListener("webglcontextlost", this.onContextLost);

    const pmrem = new THREE.PMREMGenerator(this.renderer);
    const roomEnv = new RoomEnvironment();
    this.envTex = pmrem.fromScene(roomEnv, 0.04).texture;
    this.scene.environment = this.envTex;
    roomEnv.dispose();
    pmrem.dispose();

    this.fog = new THREE.Fog("#1e2329", 65, 220);
    this.scene.fog = this.fog;
    this.scene.add(this.hemi, this.sun, this.sun.target);

    if (this.high) {
      this.sun.castShadow = true;
      this.sun.shadow.mapSize.set(1024, 1024);
      const sc = this.sun.shadow.camera;
      sc.left = -22;
      sc.right = 22;
      sc.top = 22;
      sc.bottom = -22;
      sc.near = 1;
      sc.far = 180;
      this.sun.shadow.bias = -0.0004;
      this.sun.shadow.normalBias = 0.03;
      this.sun.shadow.radius = 3;
    }

    this.unit = this.geo(new THREE.BoxGeometry(1, 1, 1));
    this.buildSky();
    this.buildArVrLearningWorld();

    if (this.opts.reducedMotion) {
      this.intro = 1;
    }

    const rect = canvas.getBoundingClientRect();
    this.resize(
      rect.width || window.innerWidth || 1280,
      rect.height || window.innerHeight || 800
    );

    this.apply(0);
    this.warm = this.warmUp();
    void this.loadRealGlbModels();
  }

  /**
   * Compile every shader before the first frame without blocking the main
   * thread (KHR_parallel_shader_compile). The old warm-up rendered twice
   * synchronously, and the program links froze the page for seconds; hidden
   * stage objects are compiled too, so later scroll stages don't stall.
   */
  private async warmUp() {
    const hidden: THREE.Object3D[] = [];
    const culled: THREE.Object3D[] = [];
    this.scene.traverse((obj) => {
      if (!obj.visible) {
        obj.visible = true;
        hidden.push(obj);
      }
      if (obj.frustumCulled) {
        obj.frustumCulled = false;
        culled.push(obj);
      }
    });
    try {
      await this.renderer.compileAsync(this.scene, this.camera);
    } catch {
      // Falls back to compiling on the first render
    }
    hidden.forEach((obj) => {
      obj.visible = false;
    });
    culled.forEach((obj) => {
      obj.frustumCulled = true;
    });
    if (this.disposed) return;
    this.warmed = true;
    this.apply(0);
    this.renderer.shadowMap.needsUpdate = true;
    this.last = performance.now();
    this.requestFrame();
  }

  setHero(v: number) {
    if (this.disposed) return;
    this.target.hero = clamp01(v);
    this.requestFrame();
  }

  setBuild(v: number) {
    if (this.disposed) return;
    this.target.build = clamp01(v);
    this.requestFrame();
  }

  setPointer(x: number, y: number) {
    if (this.disposed || this.opts.reducedMotion) return;
    this.target.px = x;
    this.target.py = y;
    this.requestFrame();
  }

  setLayout(layout: "split" | "center") {
    if (this.disposed) return;
    if (layout !== this.opts.layout) {
      this.opts.layout = layout;
      this.resize(this.width, this.height);
    }
  }

  setVisible(vis: boolean) {
    if (this.disposed) return;
    this.visible = vis;
    if (vis) {
      this.last = performance.now();
      this.requestFrame();
    } else if (this.raf) {
      cancelAnimationFrame(this.raf);
      this.raf = 0;
    }
  }

  resize(w?: number, h?: number) {
    if (this.disposed || !this.renderer) return;
    const resolvedW =
      w ?? (this.canvas.clientWidth || window.innerWidth || 1280);
    const resolvedH =
      h ?? (this.canvas.clientHeight || window.innerHeight || 800);
    this.width = Math.max(1, resolvedW);
    this.height = Math.max(1, resolvedH);
    this.renderer.setSize(this.width, this.height, false);
    const nw = this.width;
    const nh = this.height;
    const vp =
      this.opts.layout === "split"
        ? { x: nw * 0.41, y: nh * 0.08, w: nw * 0.55, h: nh * 0.84 }
        : { x: nw * 0.04, y: nh * 0.08, w: nw * 0.92, h: nh * 0.44 };
    this.camera.aspect = vp.w / vp.h;
    this.camera.setViewOffset(vp.w, vp.h, -vp.x, -vp.y, nw, nh);
    this.camera.updateProjectionMatrix();
    this.renderer.shadowMap.needsUpdate = true;
    this.requestFrame();
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    cancelAnimationFrame(this.raf);
    this.canvas.removeEventListener("webglcontextlost", this.onContextLost);
    this.batches.forEach((b) => b.mesh?.dispose());
    this.geometries.forEach((g) => g.dispose());
    this.materials.forEach((m) => m.dispose());
    this.textures.forEach((t) => t.dispose());
    this.lines?.geometry.dispose();
    this.envTex?.dispose();
    this.renderer?.dispose();
  }

  private geo<T extends THREE.BufferGeometry>(g: T): T {
    this.geometries.push(g);
    return g;
  }

  private mat<T extends THREE.Material>(m: T): T {
    this.materials.push(m);
    return m;
  }

  private tex(canvas: HTMLCanvasElement, repeat = false) {
    const t = new THREE.CanvasTexture(canvas);
    t.colorSpace = THREE.SRGBColorSpace;
    if (repeat) {
      t.wrapS = t.wrapT = THREE.RepeatWrapping;
    }
    t.anisotropy = Math.min(8, this.renderer.capabilities.getMaxAnisotropy());
    this.textures.push(t);
    return t;
  }

  private batch(
    geo: THREE.BufferGeometry,
    mat: THREE.Material,
    grow: "y" | "xyz" | "fly" | "none",
    dur: number,
    shadows?: { cast: boolean; receive: boolean }
  ) {
    const b = new AnimatedBatch(geo, mat, grow, dur, shadows);
    this.batches.push(b);
    return b;
  }

  private box(
    mat: THREE.Material,
    x: number,
    y: number,
    z: number,
    sx: number,
    sy: number,
    sz: number,
    parent: THREE.Object3D,
    castShadow = true
  ) {
    const m = new THREE.Mesh(this.unit, mat);
    m.position.set(x, y, z);
    m.scale.set(sx, sy, sz);
    m.castShadow = castShadow;
    m.receiveShadow = true;
    parent.add(m);
    return m;
  }

  private makeHudCardTexture(
    code: string,
    title: string,
    subtitle: string,
    accent: string,
    mode: "wave" | "poly" | "code"
  ) {
    const { c, g } = makeCanvas(512, 320);
    // Translucent dark architectural plate
    g.fillStyle = "rgba(14, 17, 22, 0.92)";
    g.fillRect(0, 0, 512, 320);

    // Subtle blueprint grid
    g.strokeStyle = "rgba(244, 239, 230, 0.07)";
    g.lineWidth = 1;
    for (let x = 0; x <= 512; x += 32) {
      g.beginPath();
      g.moveTo(x, 0);
      g.lineTo(x, 320);
      g.stroke();
    }
    for (let y = 0; y <= 320; y += 32) {
      g.beginPath();
      g.moveTo(0, y);
      g.lineTo(512, y);
      g.stroke();
    }

    // Top copper bar & border
    g.fillStyle = accent;
    g.fillRect(0, 0, 512, 6);
    g.strokeStyle = "rgba(208, 132, 95, 0.55)";
    g.lineWidth = 3;
    g.strokeRect(2, 2, 508, 316);

    // Header metadata
    g.fillStyle = accent;
    g.font = "600 18px monospace";
    g.fillText(code, 28, 42);

    g.fillStyle = "rgba(244, 239, 230, 0.55)";
    g.font = "15px monospace";
    g.fillText("MEIPORUL SPATIAL OS · LIVE", 230, 42);

    // Title & subtitle
    g.fillStyle = "#fbf9f4";
    g.font = "300 32px Georgia, serif";
    g.fillText(title, 28, 92);

    g.fillStyle = "#c7b89f";
    g.font = "17px sans-serif";
    g.fillText(subtitle, 28, 122);

    // Mode-specific interactive diagram
    g.strokeStyle = accent;
    g.lineWidth = 2.5;
    if (mode === "wave") {
      // Fourier / Quantum wave simulation
      g.beginPath();
      for (let x = 28; x <= 484; x += 4) {
        const t = (x - 28) / 456;
        const y =
          215 +
          Math.sin(t * Math.PI * 4) * 38 * Math.sin(t * Math.PI) +
          Math.cos(t * Math.PI * 10) * 10;
        if (x === 28) g.moveTo(x, y);
        else g.lineTo(x, y);
      }
      g.stroke();

      g.strokeStyle = "rgba(125, 211, 252, 0.65)";
      g.beginPath();
      for (let x = 28; x <= 484; x += 4) {
        const t = (x - 28) / 456;
        const y = 215 + Math.cos(t * Math.PI * 3) * 28;
        if (x === 28) g.moveTo(x, y);
        else g.lineTo(x, y);
      }
      g.stroke();
    } else if (mode === "poly") {
      // 3D Vector & Matrix projection
      const cx = 140;
      const cy = 218;
      const r = 56;
      g.beginPath();
      for (let i = 0; i < 6; i++) {
        const a = (i * Math.PI) / 3 - Math.PI / 6;
        const px = cx + Math.cos(a) * r;
        const py = cy + Math.sin(a) * r;
        if (i === 0) g.moveTo(px, py);
        else g.lineTo(px, py);
      }
      g.closePath();
      g.stroke();

      g.fillStyle = "rgba(244, 239, 230, 0.85)";
      g.font = "16px monospace";
      g.fillText("∇ × E = -∂B/∂t", 240, 185);
      g.fillText("det(A - λI) = 0", 240, 218);
      g.fillText("FOV: 110° STEREO", 240, 251);
    } else {
      // Interactive lab telemetry bars
      const bars = [0.72, 0.88, 0.64, 0.94, 0.81, 0.96, 0.78, 0.91];
      bars.forEach((val, idx) => {
        const bx = 34 + idx * 56;
        const bh = val * 110;
        g.fillStyle = idx % 2 === 0 ? accent : "rgba(125, 211, 252, 0.75)";
        g.fillRect(bx, 276 - bh, 34, bh);
      });
    }

    // Bottom status rule
    g.fillStyle = "rgba(244, 239, 230, 0.6)";
    g.font = "14px monospace";
    g.fillText("OPTICAL SYNC: 120Hz · LATENCY 1.8ms", 28, 302);

    return this.tex(c, false);
  }

  /** Honed dark granite: fine mineral speckle over soft tonal drift. */
  private makeStoneTexture() {
    const { c, g } = makeCanvas(1024, 1024);
    g.fillStyle = "#2c2f34";
    g.fillRect(0, 0, 1024, 1024);
    for (let i = 0; i < 160; i++) {
      const x = Math.random() * 1024;
      const y = Math.random() * 1024;
      const r = 30 + Math.random() * 90;
      const grad = g.createRadialGradient(x, y, 0, x, y, r);
      const tone = Math.random() < 0.5 ? "255,255,255" : "0,0,0";
      grad.addColorStop(0, `rgba(${tone},0.05)`);
      grad.addColorStop(1, `rgba(${tone},0)`);
      g.fillStyle = grad;
      g.fillRect(x - r, y - r, r * 2, r * 2);
    }
    // Mineral speckle written straight into pixels: one pass instead of
    // tens of thousands of fillRect calls (which cost ~0.5s of main thread).
    const img = g.getImageData(0, 0, 1024, 1024);
    const d = img.data;
    for (let i = 0; i < d.length; i += 4) {
      const r = Math.random();
      if (r > 0.055) continue;
      if (r < 0.03) {
        const k = 0.35 + Math.random() * 0.4;
        d[i] *= 1 - k * 0.6;
        d[i + 1] *= 1 - k * 0.6;
        d[i + 2] *= 1 - k * 0.55;
      } else if (r < 0.05) {
        const k = 0.18 + Math.random() * 0.3;
        d[i] += (120 - d[i]) * k;
        d[i + 1] += (124 - d[i + 1]) * k;
        d[i + 2] += (130 - d[i + 2]) * k;
      } else {
        const k = 0.25 + Math.random() * 0.35;
        d[i] += (205 - d[i]) * k;
        d[i + 1] += (196 - d[i + 1]) * k;
        d[i + 2] += (182 - d[i + 2]) * k;
      }
    }
    g.putImageData(img, 0, 0);
    const t = this.tex(c, true);
    t.repeat.set(2, 2);
    return t;
  }

  /** Roughness map for the top plate: fine concentric brushing (cap UVs are planar). */
  private makeBrushedTexture() {
    const size = 1024;
    const { c, g } = makeCanvas(size, size);
    g.fillStyle = "#808080";
    g.fillRect(0, 0, size, size);
    const mid = size / 2;
    for (let r = 2; r < mid; r += 1.25) {
      const v = 96 + Math.floor(Math.random() * 64);
      g.strokeStyle = `rgba(${v},${v},${v},${0.35 + Math.random() * 0.4})`;
      g.lineWidth = 0.6 + Math.random() * 0.8;
      g.beginPath();
      g.arc(mid, mid, r, 0, Math.PI * 2);
      g.stroke();
    }
    const t = this.tex(c);
    t.colorSpace = THREE.NoColorSpace;
    return t;
  }

  private makeTextures() {
    const dotC = makeCanvas(64, 64);
    {
      const grad = dotC.g.createRadialGradient(32, 32, 0, 32, 32, 32);
      grad.addColorStop(0, "rgba(255,255,255,1)");
      grad.addColorStop(1, "rgba(255,255,255,0)");
      dotC.g.fillStyle = grad;
      dotC.g.fillRect(0, 0, 64, 64);
    }

    const glowC = makeCanvas(128, 128);
    {
      const grad = glowC.g.createRadialGradient(64, 64, 0, 64, 64, 64);
      grad.addColorStop(0, "rgba(240,160,110,0.92)");
      grad.addColorStop(0.5, "rgba(208,132,95,0.35)");
      grad.addColorStop(1, "rgba(240,160,110,0)");
      glowC.g.fillStyle = grad;
      glowC.g.fillRect(0, 0, 128, 128);
    }

    // Lens waveguide HUD reticle texture
    const lensHudC = makeCanvas(256, 256);
    {
      const { g } = lensHudC;
      g.clearRect(0, 0, 256, 256);
      const grad = g.createRadialGradient(128, 128, 12, 128, 128, 118);
      grad.addColorStop(0, "rgba(125, 211, 252, 0.32)");
      grad.addColorStop(0.55, "rgba(208, 132, 95, 0.24)");
      grad.addColorStop(1, "rgba(14, 17, 22, 0.05)");
      g.fillStyle = grad;
      g.beginPath();
      g.arc(128, 128, 118, 0, Math.PI * 2);
      g.fill();

      g.strokeStyle = "rgba(240, 205, 185, 0.65)";
      g.lineWidth = 2;
      for (const r of [38, 68, 98]) {
        g.beginPath();
        g.arc(128, 128, r, 0, Math.PI * 2);
        g.stroke();
      }
      g.beginPath();
      g.moveTo(70, 128);
      g.lineTo(186, 128);
      g.moveTo(128, 70);
      g.lineTo(128, 186);
      g.stroke();
    }

    return {
      dot: this.tex(dotC.c, false),
      glow: this.tex(glowC.c, false),
      lensHud: this.tex(lensHudC.c, false),
      hud1: this.makeHudCardTexture(
        "LAB—01 · PHYSICS & WAVEGUIDES",
        "Quantum & Optical Simulation",
        "Interactive browser lab projected in 3D space",
        "#d0845f",
        "wave"
      ),
      hud2: this.makeHudCardTexture(
        "MEIPORUL—02 · SPATIAL MATH",
        "3D Linear Algebra & Vectors",
        "Rotate eigen-spaces & manifolds in real time",
        "#e0a282",
        "poly"
      ),
      hud3: this.makeHudCardTexture(
        "SEYAPPADUPORUL—03 · SYSTEMS",
        "Live Neural & Code Telemetry",
        "Full-stack & AI pipeline execution metrics",
        "#d0845f",
        "code"
      ),
    };
  }

  private buildSky() {
    this.skyMat = this.mat(
      new THREE.ShaderMaterial({
        side: THREE.BackSide,
        depthWrite: false,
        fog: false,
        toneMapped: false,
        uniforms: {
          top: { value: new THREE.Color() },
          horizon: { value: new THREE.Color() },
          sunDir: { value: new THREE.Vector3(0, 1, 0) },
          sunColor: { value: new THREE.Color() },
          glow: { value: 0 },
        },
        vertexShader: `
          varying vec3 vDir;
          void main() {
            vec4 world = modelMatrix * vec4(position, 1.0);
            vDir = world.xyz - cameraPosition;
            gl_Position = projectionMatrix * viewMatrix * world;
          }`,
        fragmentShader: `
          uniform vec3 top;
          uniform vec3 horizon;
          uniform vec3 sunDir;
          uniform vec3 sunColor;
          uniform float glow;
          varying vec3 vDir;
          void main() {
            vec3 d = normalize(vDir);
            vec3 col = mix(horizon, top, smoothstep(-0.02, 0.5, d.y));
            float s = max(dot(d, sunDir), 0.0);
            col += sunColor * (pow(s, 10.0) * 0.32 + pow(s, 400.0) * 1.2) * glow
              * smoothstep(-0.08, 0.04, d.y);
            gl_FragColor = vec4(col, 1.0);
            #include <colorspace_fragment>
          }`,
      })
    );
    const dome = new THREE.Mesh(
      this.geo(new THREE.SphereGeometry(600, 32, 16)),
      this.skyMat
    );
    dome.frustumCulled = false;
    this.scene.add(dome);
  }

  private buildArVrLearningWorld() {
    const tex = this.makeTextures();
    const env = this.envTex;
    const unit = this.unit;

    this.materials.push(
      this.litMat,
      this.cyanGlowMat,
      this.lampMat,
      this.beaconMat,
      this.lineMat,
      this.boundaryMat,
      this.frustumMat
    );

    const stdMat = (params: THREE.MeshStandardMaterialParameters) =>
      this.mat(new THREE.MeshStandardMaterial(params));

    // Architectural & Hardware Materials
    const titaniumDark = stdMat({
      color: "#1e2228",
      metalness: 0.72,
      roughness: 0.26,
      envMap: env,
      envMapIntensity: 1.1,
    });
    const limestoneBody = stdMat({
      color: "#e9e1d2",
      metalness: 0.12,
      roughness: 0.45,
      envMap: env,
      envMapIntensity: 0.6,
    });
    const brushedCopper = stdMat({
      color: "#c8754c",
      metalness: 0.85,
      roughness: 0.24,
      envMap: env,
      envMapIntensity: 1.35,
    });
    const warmGold = stdMat({
      color: "#e2a468",
      metalness: 0.88,
      roughness: 0.2,
      envMap: env,
      envMapIntensity: 1.4,
    });
    const holoPolyMat = stdMat({
      color: "#d0845f",
      emissive: "#bd6a45",
      emissiveIntensity: 0.65,
      metalness: 0.6,
      roughness: 0.2,
      wireframe: false,
    });
    const holoWireMat = this.mat(
      new THREE.MeshBasicMaterial({
        color: "#ffd8b8",
        wireframe: true,
        transparent: true,
        opacity: 0.75,
      })
    );

    // Bounding corners for automatic fitDistance framing
    for (const x of [-10.5, 10.5]) {
      for (const y of [-0.5, 10.2]) {
        for (const z of [-8.5, 8.5]) {
          this.corners.push(new THREE.Vector3(x, y, z));
        }
      }
    }
    this.center.set(0, 4.3, 0);

    // Ground studio floor
    const ground = new THREE.Mesh(
      this.geo(new THREE.PlaneGeometry(1200, 1200)),
      this.mat(new THREE.MeshLambertMaterial({ color: "#14171b" }))
    );
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    this.scene.add(ground);

    // Display plinth: honed stone base with chamfered edges, a satin
    // aluminium top plate brushed in concentric rings, and a slim copper rim
    // where the two meet. The base is lathed so its edges carry real bevels.
    const stoneMat = stdMat({
      map: this.makeStoneTexture(),
      roughness: 0.86,
      metalness: 0.02,
      envMap: env,
      envMapIntensity: 0.35,
    });
    const plateMat = stdMat({
      color: "#4a5058",
      roughnessMap: this.makeBrushedTexture(),
      roughness: 0.46,
      metalness: 0.9,
      envMap: env,
      envMapIntensity: 0.55,
    });
    const grooveMat = stdMat({
      color: "#0b0c0e",
      roughness: 0.7,
      metalness: 0.3,
    });

    const baseProfile = [
      [0, 0],
      [12.05, 0],
      [12.2, 0.05],
      [12.2, 0.28],
      [12.14, 0.33],
      [12.02, 0.36],
      [0, 0.36],
    ].map(([r, y]) => new THREE.Vector2(r, y));
    const baseGeo = this.geo(new THREE.LatheGeometry(baseProfile, 128));
    // Lathe UVs run around and along the profile, which smears the speckle
    // into radial streaks; project them top-down instead.
    {
      const pos = baseGeo.getAttribute("position");
      const uv = baseGeo.getAttribute("uv");
      for (let i = 0; i < pos.count; i++) {
        uv.setXY(i, pos.getX(i) / 24.4 + 0.5, pos.getZ(i) / 24.4 + 0.5);
      }
      uv.needsUpdate = true;
    }
    const baseDisc = new THREE.Mesh(baseGeo, stoneMat);
    baseDisc.castShadow = this.high;
    baseDisc.receiveShadow = true;
    this.scene.add(baseDisc);

    // Shadow gap between stone and plate
    const groove = new THREE.Mesh(
      this.geo(new THREE.TorusGeometry(8.62, 0.07, 10, 128)),
      grooveMat
    );
    groove.rotation.x = Math.PI / 2;
    groove.position.set(0, 0.36, 0);
    this.scene.add(groove);

    const innerDisc = new THREE.Mesh(
      this.geo(new THREE.CylinderGeometry(8.32, 8.46, 0.15, 128)),
      plateMat
    );
    innerDisc.position.set(0, 0.435, 0);
    innerDisc.castShadow = this.high;
    innerDisc.receiveShadow = true;
    this.scene.add(innerDisc);

    // Polished copper rim on the plate edge (the bevel that catches light)
    const copperRingBase = new THREE.Mesh(
      this.geo(new THREE.TorusGeometry(8.33, 0.035, 12, 160)),
      brushedCopper
    );
    copperRingBase.rotation.x = Math.PI / 2;
    copperRingBase.position.set(0, 0.505, 0);
    this.scene.add(copperRingBase);

    // Soft contact shadow under the floating headset, so it reads as
    // hovering above the plate rather than pasted over it
    const shadowCanvas = makeCanvas(256, 256);
    {
      const { g } = shadowCanvas;
      const grad = g.createRadialGradient(128, 128, 0, 128, 128, 128);
      grad.addColorStop(0, "rgba(0,0,0,0.62)");
      grad.addColorStop(0.45, "rgba(0,0,0,0.32)");
      grad.addColorStop(1, "rgba(0,0,0,0)");
      g.fillStyle = grad;
      g.fillRect(0, 0, 256, 256);
    }
    this.contactShadow = new THREE.Mesh(
      this.geo(new THREE.PlaneGeometry(10.5, 7.5)),
      this.mat(
        new THREE.MeshBasicMaterial({
          map: this.tex(shadowCanvas.c),
          transparent: true,
          depthWrite: false,
          color: "#000000",
        })
      )
    );
    this.contactShadow.rotation.x = -Math.PI / 2;
    this.contactShadow.position.set(0, 0.515, 0.2);
    this.contactShadow.renderOrder = 1;
    this.contactShadow.visible = false;
    this.scene.add(this.contactShadow);

    // Dashed copper calibration boundary ring
    const boundaryPts: THREE.Vector3[] = [];
    for (let i = 0; i <= 96; i++) {
      const a = (i / 96) * Math.PI * 2;
      boundaryPts.push(vec3(Math.cos(a) * 10.4, 0.4, Math.sin(a) * 10.4));
    }
    const boundaryLine = new THREE.Line(
      this.geo(new THREE.BufferGeometry().setFromPoints(boundaryPts)),
      this.boundaryMat
    );
    boundaryLine.computeLineDistances();
    this.scene.add(boundaryLine);

    // Warm ground glow
    this.glowMat = this.mat(
      new THREE.MeshBasicMaterial({
        map: tex.glow,
        transparent: true,
        opacity: 0,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      })
    );
    const glowPlane = new THREE.Mesh(
      this.geo(new THREE.PlaneGeometry(36, 36)),
      this.glowMat
    );
    glowPlane.rotation.x = -Math.PI / 2;
    glowPlane.position.set(0, 0.53, 0);
    this.scene.add(glowPlane);

    // Studio perimeter light pillars
    const pillarBatch = this.batch(unit, titaniumDark, "y", 0.15);
    const lampBatch = this.batch(unit, this.lampMat, "none", 1, {
      cast: false,
      receive: false,
    });
    for (let i = 0; i < 8; i++) {
      const ang = (i / 8) * Math.PI * 2 + Math.PI / 8;
      const rx = Math.cos(ang) * 11.0;
      const rz = Math.sin(ang) * 11.0;
      pillarBatch.add({
        x: rx,
        y: 1.1,
        z: rz,
        sx: 0.14,
        sy: 1.5,
        sz: 0.14,
        t0: 0,
        ry: -ang,
      });
      lampBatch.add({
        x: rx,
        y: 1.88,
        z: rz,
        sx: 0.24,
        sy: 0.08,
        sz: 0.24,
        t0: 0,
        ry: -ang,
      });
    }

    this.scene.add(this.rigRoot);
    // Product decision: the only headset on stage is the real Meta Quest 3S
    // GLB. Nothing procedural stands in while it fetches or if it fails.
    this.realHeadsetRoot.position.set(0, 5.3, 0.2);
    this.rigRoot.add(this.realHeadsetRoot);

    // Central optical pedestal stand supporting the headset during calibration
    const standBatch = this.batch(unit, titaniumDark, "y", 0.12);
    standBatch.add({
      x: 0,
      y: 1.45,
      z: -0.6,
      sx: 0.34,
      sy: 2.1,
      sz: 0.34,
      t0: 0.02,
      t1: 0.86,
    });
    standBatch.add({
      x: 0,
      y: 2.55,
      z: -0.1,
      sx: 1.6,
      sy: 0.14,
      sz: 1.2,
      t0: 0.05,
      t1: 0.85,
    });

    // ========================================================================
    // STAGE 02-03: TWIN PRECISION OPTICAL CALIBRATION GANTRIES
    // ========================================================================
    // Each gantry is a bench-mounted optical calibration arm: weighted base
    // with bolts, anodized column with clamp collars, a jointed boom with a
    // parallel stay rod, and a sensor head with a glass lens and LED ring.
    const powderCoat = stdMat({
      color: "#25282d",
      roughness: 0.68,
      metalness: 0.35,
      envMap: env,
      envMapIntensity: 0.6,
    });
    const anodized = stdMat({
      color: "#b4bac2",
      roughness: 0.3,
      metalness: 0.92,
      envMap: env,
      envMapIntensity: 0.9,
    });
    const housing = stdMat({
      color: "#17181b",
      roughness: 0.42,
      metalness: 0.25,
      envMap: env,
      envMapIntensity: 0.7,
    });
    const lensGlass = stdMat({
      color: "#06090c",
      roughness: 0.04,
      metalness: 0.6,
      envMap: env,
      envMapIntensity: 1.6,
    });
    const cableMat = stdMat({ color: "#0e0f11", roughness: 0.75 });

    const cyl = (r: number, h: number, seg = 32, rTop = r) =>
      this.geo(new THREE.CylinderGeometry(rTop, r, h, seg));
    const part = (
      geo: THREE.BufferGeometry,
      mat: THREE.Material,
      parent: THREE.Object3D,
      x: number,
      y: number,
      z: number,
      rx = 0,
      rz = 0
    ) => {
      const m = new THREE.Mesh(geo, mat);
      m.position.set(x, y, z);
      m.rotation.set(rx, 0, rz);
      m.castShadow = this.high;
      m.receiveShadow = true;
      parent.add(m);
      return m;
    };
    const ring = (r: number, tube: number) =>
      this.geo(new THREE.TorusGeometry(r, tube, 10, 48));
    const boltGeo = cyl(0.055, 0.06, 6);

    for (const [side, gantry, arm] of [
      [-1, this.leftGantry, this.leftGantryArm] as const,
      [1, this.rightGantry, this.rightGantryArm] as const,
    ]) {
      gantry.position.set(side * 7.2, 0.5, 0.4);
      this.scene.add(gantry);

      // Weighted base: chamfered disc plus a raised boss, four cap bolts
      part(cyl(0.82, 0.22, 48, 0.76), powderCoat, gantry, 0, 0.11, 0);
      part(cyl(0.48, 0.14, 40, 0.42), powderCoat, gantry, 0, 0.29, 0);
      for (let i = 0; i < 4; i++) {
        const a = (i / 4) * Math.PI * 2 + Math.PI / 4;
        part(boltGeo, anodized, gantry, Math.cos(a) * 0.6, 0.25, Math.sin(a) * 0.6);
      }

      // Column with clamp collars and a copper index ring
      part(cyl(0.14, 3.3), anodized, gantry, 0, 1.99, 0);
      part(cyl(0.21, 0.2), powderCoat, gantry, 0, 0.46, 0);
      part(cyl(0.22, 0.26), powderCoat, gantry, 0, 3.5, 0);
      part(ring(0.22, 0.022), brushedCopper, gantry, 0, 3.36, 0, Math.PI / 2);

      arm.position.set(0, 3.8, 0);
      gantry.add(arm);

      // Shoulder joint: hub on the Z axis with copper bearing rings
      part(cyl(0.27, 0.44), housing, arm, 0, 0, 0, Math.PI / 2);
      part(ring(0.27, 0.024), brushedCopper, arm, 0, 0, 0.22);
      part(ring(0.27, 0.024), brushedCopper, arm, 0, 0, -0.22);

      // Boom with a parallel stay rod and link blocks
      const reach = 2.2;
      part(cyl(0.1, reach - 0.3), anodized, arm, -side * (reach / 2), 0, 0, 0, Math.PI / 2);
      part(cyl(0.035, reach - 0.4), anodized, arm, -side * (reach / 2), 0.2, 0, 0, Math.PI / 2);
      this.box(housing, -side * 0.32, 0.1, 0, 0.12, 0.34, 0.16, arm);
      this.box(housing, -side * (reach - 0.32), 0.1, 0, 0.12, 0.34, 0.16, arm);

      // Elbow hub, wrist and sensor head
      const tip = -side * reach;
      part(cyl(0.18, 0.36), housing, arm, tip, 0, 0, Math.PI / 2);
      part(ring(0.18, 0.018), brushedCopper, arm, tip, 0, 0.18);
      part(cyl(0.075, 0.34), anodized, arm, tip, -0.32, 0);
      part(cyl(0.2, 0.42, 32, 0.17), housing, arm, tip, -0.66, 0);
      part(cyl(0.13, 0.04), lensGlass, arm, tip, -0.885, 0);
      part(ring(0.165, 0.016), this.cyanGlowMat, arm, tip, -0.88, 0, Math.PI / 2);

      // Signal cable along the boom, looping down behind the shoulder
      const cablePath = new THREE.CatmullRomCurve3([
        vec3(tip + side * 0.12, -0.5, 0.14),
        vec3(tip + side * 0.2, 0.08, 0.14),
        vec3(-side * (reach / 2), 0.13, 0.13),
        vec3(-side * 0.3, 0.1, 0.16),
        vec3(side * 0.05, -0.25, 0.32),
        vec3(side * 0.12, -0.75, 0.22),
      ]);
      part(
        this.geo(new THREE.TubeGeometry(cablePath, 48, 0.028, 8, false)),
        cableMat,
        arm,
        0,
        0,
        0
      );
    }

    // ========================================================================
    // STAGE 04 & 05: HOLOGRAPHIC LEARNING SUITE, 3D POLYHEDRON & GYRO RINGS
    // ========================================================================
    this.holoGroup.position.set(0, 6.3, 0.6);
    this.rigRoot.add(this.holoGroup);

    // Central Meiporul Sacred Geometric Core (Icosahedron + Wireframe cage)
    this.holoGroup.add(this.holoCore);
    const icoSolid = new THREE.Mesh(
      this.geo(new THREE.IcosahedronGeometry(1.15, 0)),
      holoPolyMat
    );
    const icoWire = new THREE.Mesh(
      this.geo(new THREE.IcosahedronGeometry(1.42, 1)),
      holoWireMat
    );
    this.holoCore.add(icoSolid, icoWire);

    // Double-Helix / Atomic Lattice nodes around the core
    this.holoGroup.add(this.helixGroup);
    const nodeSphereGeo = this.geo(new THREE.SphereGeometry(0.14, 14, 12));
    for (let i = 0; i < 16; i++) {
      const t = (i / 15) * Math.PI * 2;
      const r = 2.05;
      const y = (i / 15 - 0.5) * 2.2;
      const n1 = new THREE.Mesh(
        nodeSphereGeo,
        i % 2 === 0 ? brushedCopper : this.cyanGlowMat
      );
      n1.position.set(Math.cos(t) * r, y, Math.sin(t) * r);
      const n2 = new THREE.Mesh(
        nodeSphereGeo,
        i % 2 === 0 ? warmGold : this.litMat
      );
      n2.position.set(
        Math.cos(t + Math.PI) * r,
        y,
        Math.sin(t + Math.PI) * r
      );
      this.helixGroup.add(n1, n2);
    }

    // Three Gyroscopic Knowledge Rings (Meiporul · Utporul · Seyappaduporul)
    const gyroConfigs = [
      { grp: this.gyroRing1, rad: 3.1, tube: 0.045, mat: brushedCopper },
      { grp: this.gyroRing2, rad: 3.85, tube: 0.038, mat: warmGold },
      { grp: this.gyroRing3, rad: 4.55, tube: 0.032, mat: limestoneBody },
    ];
    for (const cfg of gyroConfigs) {
      this.holoGroup.add(cfg.grp);
      const ringMesh = new THREE.Mesh(
        this.geo(new THREE.TorusGeometry(cfg.rad, cfg.tube, 14, 96)),
        cfg.mat
      );
      cfg.grp.add(ringMesh);

      // Orbital knowledge node satellites on each ring
      for (let k = 0; k < 4; k++) {
        const a = (k / 4) * Math.PI * 2;
        const sat = new THREE.Mesh(
          this.geo(new THREE.SphereGeometry(0.13, 12, 10)),
          k % 2 === 0 ? this.litMat : this.cyanGlowMat
        );
        sat.position.set(Math.cos(a) * cfg.rad, Math.sin(a) * cfg.rad, 0);
        cfg.grp.add(sat);
      }
    }

    // Three Floating Spatial UI Learning Panels in an arc
    this.holoGroup.add(this.hudScreensGroup);
    const panelGeo = this.geo(new THREE.PlaneGeometry(2.9, 1.82));
    const framePlaneGeo = this.geo(new THREE.PlaneGeometry(3.02, 1.94));
    const hudSpecs = [
      { tex: tex.hud1, x: -3.7, y: -0.35, z: 1.6, ry: 0.42 },
      { tex: tex.hud2, x: 0, y: 1.65, z: 2.2, ry: 0 },
      { tex: tex.hud3, x: 3.7, y: -0.35, z: 1.6, ry: -0.42 },
    ];
    for (const hs of hudSpecs) {
      const holder = new THREE.Group();
      holder.position.set(hs.x, hs.y, hs.z);
      holder.rotation.y = hs.ry;

      const backFrame = new THREE.Mesh(
        framePlaneGeo,
        this.mat(
          new THREE.MeshBasicMaterial({
            color: "#d0845f",
            transparent: true,
            opacity: 0.38,
            side: THREE.DoubleSide,
          })
        )
      );
      backFrame.position.z = -0.02;
      const screenMesh = new THREE.Mesh(
        panelGeo,
        this.mat(
          new THREE.MeshBasicMaterial({
            map: hs.tex,
            transparent: true,
            opacity: 0.95,
            side: THREE.DoubleSide,
            toneMapped: false,
          })
        )
      );
      holder.add(backFrame, screenMesh);
      this.hudScreensGroup.add(holder);
    }

    // Optical Waveguide Projection Frustum Beams from the Left & Right Lenses to Hologram Core
    this.beamMat = this.mat(
      new THREE.MeshBasicMaterial({
        color: "#e09868",
        transparent: true,
        opacity: 0,
        side: THREE.DoubleSide,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      })
    );
    const coneGeo = this.geo(
      new THREE.CylinderGeometry(1.65, 0.85, 3.1, 32, 1, true)
    );
    this.beamLeft = new THREE.Mesh(coneGeo, this.beamMat);
    this.beamLeft.position.set(-1.35, 4.85, 0.85);
    this.beamLeft.rotation.z = -0.32;
    this.rigRoot.add(this.beamLeft);

    this.beamRight = new THREE.Mesh(coneGeo, this.beamMat);
    this.beamRight.position.set(1.35, 4.85, 0.85);
    this.beamRight.rotation.z = 0.32;
    this.rigRoot.add(this.beamRight);

    // ========================================================================
    // BLUEPRINT CAD WIREFRAME OVERLAY (this.lines - draws on load via intro)
    // ========================================================================
    const bpVerts: number[] = [];
    const pushSeg = (
      a: [number, number, number],
      b: [number, number, number]
    ) => bpVerts.push(...a, ...b);

    // CAD wireframe of the upper Orbital Knowledge Sphere
    for (let ring = 0; ring < 3; ring++) {
      const N = 36;
      const rad = 3.2 + ring * 0.65;
      for (let i = 0; i < N; i++) {
        const a0 = (i / N) * Math.PI * 2;
        const a1 = ((i + 1) / N) * Math.PI * 2;
        if (ring === 0) {
          pushSeg(
            [Math.cos(a0) * rad, 6.3 + Math.sin(a0) * rad, 0.6],
            [Math.cos(a1) * rad, 6.3 + Math.sin(a1) * rad, 0.6]
          );
        } else if (ring === 1) {
          pushSeg(
            [Math.cos(a0) * rad, 6.3, 0.6 + Math.sin(a0) * rad],
            [Math.cos(a1) * rad, 6.3, 0.6 + Math.sin(a1) * rad]
          );
        } else {
          pushSeg(
            [
              Math.cos(a0) * rad * 0.85,
              6.3 + Math.sin(a0) * rad * 0.85,
              0.6 + Math.cos(a0) * rad * 0.5,
            ],
            [
              Math.cos(a1) * rad * 0.85,
              6.3 + Math.sin(a1) * rad * 0.85,
              0.6 + Math.cos(a1) * rad * 0.5,
            ]
          );
        }
      }
    }

    for (const b of this.batches) {
      b.build(this.rigRoot);
    }

    const lineGeo = this.geo(new THREE.BufferGeometry());
    lineGeo.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(bpVerts, 3)
    );
    this.lineVertexCount = bpVerts.length / 3;
    this.lines = new THREE.LineSegments(lineGeo, this.lineMat);
    this.rigRoot.add(this.lines);

    // Floating photon knowledge particles
    if (this.high) {
      const count = 180;
      const positions = new Float32Array(count * 3);
      this.dustSeeds = new Float32Array(count * 3);
      for (let i = 0; i < count; i++) {
        const a = (i / count) * Math.PI * 2 * 5;
        const r = 1.2 + (i % 17) * 0.45;
        this.dustSeeds[i * 3] = Math.cos(a) * r;
        this.dustSeeds[i * 3 + 1] = 1.0 + (i % 23) * 0.38;
        this.dustSeeds[i * 3 + 2] = Math.sin(a) * r;
      }
      const dustGeo = this.geo(new THREE.BufferGeometry());
      dustGeo.setAttribute(
        "position",
        new THREE.Float32BufferAttribute(positions, 3)
      );
      this.dust = new THREE.Points(
        dustGeo,
        this.mat(
          new THREE.PointsMaterial({
            map: tex.dot,
            color: "#f0b27a",
            size: 0.42,
            transparent: true,
            opacity: 0,
            depthWrite: false,
            blending: THREE.AdditiveBlending,
          })
        )
      );
      this.dust.frustumCulled = false;
      this.rigRoot.add(this.dust);
    }
  }

  private async loadRealGlbModels() {
    try {
      const res = await fetch(HEADSET_MODEL.url);
      if (!res.ok || this.disposed) return;
      const buf = await res.arrayBuffer();
      if (this.disposed) return;

      const gltf = await loadGlb(buf);
      if (this.disposed) return;

      const model = gltf.scene;
      for (const name of HEADSET_MODEL.hideNodes) {
        const node = model.getObjectByName(name);
        if (node) node.removeFromParent();
      }
      model.updateMatrixWorld(true);

      const box = new THREE.Box3().setFromObject(model);
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());

      const pivot = new THREE.Group();
      model.position.sub(center);
      pivot.add(model);

      // Turn the front faceplate toward the viewer (+Z)
      pivot.rotation.set(
        HEADSET_MODEL.rotation[0],
        HEADSET_MODEL.rotation[1],
        HEADSET_MODEL.rotation[2]
      );
      const maxSpan = Math.max(size.x, size.y, size.z, 0.001);
      pivot.scale.setScalar(HEADSET_MODEL.span / maxSpan);

      // Swap the placeholder materials for physically based finishes
      model.traverse((obj: any) => {
        if (!obj?.isMesh) return;
        obj.castShadow = this.high;
        obj.receiveShadow = this.high;
        const finish = HEADSET_FINISH[obj.material?.name];
        obj.material = this.mat(
          new THREE.MeshPhysicalMaterial({
            color: "#d8d8d4",
            roughness: 0.5,
            metalness: 0,
            ...finish,
            envMap: this.envTex,
            envMapIntensity: 1.1,
          })
        );
      });

      // Scroll-driven exploded -> assembled animation. Each part drifts out
      // from the headset centre along its own direction, then locks home
      // across Stages 01..03 (outer parts later, so the shell closes last).
      this.realSubAssemblies = [];
      const parts: { node: THREE.Object3D; dir: THREE.Vector3 }[] = [];
      const centreWorld = new THREE.Box3().setFromObject(model).getCenter(
        new THREE.Vector3()
      );
      model.traverse((obj: any) => {
        if (!obj?.isMesh || !obj.parent) return;
        const partBox = new THREE.Box3().setFromObject(obj);
        // Small trims (buttons, sensors) stay attached; floating alone they
        // read as stray fragments rather than an assembly.
        const partSpan = partBox.getSize(new THREE.Vector3()).length();
        if (partSpan < maxSpan * 0.08) return;
        const c = partBox.getCenter(new THREE.Vector3()).sub(centreWorld);
        parts.push({ node: obj, dir: c });
      });
      const reach = Math.max(...parts.map((p) => p.dir.length()), 0.001);
      for (const part of parts) {
        const k = part.dir.length() / reach;
        const push =
          part.dir.length() < 1e-6
            ? new THREE.Vector3(0, 0, 0)
            : part.dir
                .clone()
                .setLength(HEADSET_MODEL.explode * maxSpan * (0.35 + k));
        // Express the push in the parent's local space so nested transforms stay correct
        const inv = new THREE.Matrix4()
          .copy(part.node.parent!.matrixWorld)
          .invert();
        const offset = centreWorld
          .clone()
          .add(push)
          .applyMatrix4(inv)
          .sub(centreWorld.clone().applyMatrix4(inv));
        const t0 = 0.06 + k * 0.22;
        this.realSubAssemblies.push({
          node: part.node,
          basePos: part.node.position.clone(),
          explodeOffset: offset,
          t0,
          t1: t0 + 0.24,
        });
      }

      // Compile the headset's materials off the main thread before mounting
      await this.warm;
      if (this.disposed) return;
      try {
        await this.renderer.compileAsync(pivot, this.camera, this.scene);
      } catch {
        // Compiles on first render instead
      }
      if (this.disposed) return;
      this.realHeadsetRoot.add(pivot);
      this.realHeadsetLoaded = true;
      this.contactShadow.visible = true;

      this.apply(0);
      this.renderer.shadowMap.needsUpdate = true;
      this.requestFrame();
    } catch {
      // Fallback procedural AR/VR rig remains active if GLB fetch fails
    }

    // Also load a real Meiporul AR mathematical 3D GLB model into Stage 05 holographic core
    try {
      const mathRes = await fetch(
        "/models/ar/Rhombic-Dodecahedron-Animated-For-Website-Done.glb"
      );
      if (!mathRes.ok || this.disposed) return;
      const mathBuf = await mathRes.arrayBuffer();
      if (this.disposed) return;
      const mathGltf = await loadGlb(mathBuf);
      if (this.disposed) return;

      const mathScene = mathGltf.scene;
      mathScene.updateMatrixWorld(true);
      const mBox = new THREE.Box3().setFromObject(mathScene);
      const mCenter = mBox.getCenter(new THREE.Vector3());
      const mSize = mBox.getSize(new THREE.Vector3());
      const mSpan = Math.max(mSize.x, mSize.y, mSize.z, 0.001);

      const mathWrap = new THREE.Group();
      mathScene.position.sub(mCenter);
      mathWrap.add(mathScene);
      mathWrap.scale.setScalar(2.6 / mSpan);

      mathScene.traverse((obj: any) => {
        if (!obj?.isMesh) return;
        const mats = Array.isArray(obj.material)
          ? obj.material
          : obj.material
          ? [obj.material]
          : [];
        for (const m of mats) {
          if (!m) continue;
          m.envMap = this.envTex;
          m.needsUpdate = true;
        }
      });

      await this.warm;
      if (this.disposed) return;
      try {
        await this.renderer.compileAsync(mathWrap, this.camera, this.scene);
      } catch {
        // Compiles on first render instead
      }
      if (this.disposed) return;
      this.holoCore.clear();
      this.holoCore.add(mathWrap);
      this.requestFrame();
    } catch {
      // Procedural icosahedron core remains in place
    }
  }

  private onContextLost = (e: Event) => {
    e.preventDefault();
    this.opts.onError?.(new Error("WebGL context lost"));
  };

  private requestFrame() {
    if (!this.raf && this.visible && !this.disposed) {
      this.raf = requestAnimationFrame(this.frame);
    }
  }

  private frame = (now: number) => {
    this.raf = 0;
    if (!this.warmed) return;
    const rawDt = Math.max(0.001, (now - (this.last || now)) / 1000);
    const dt = Math.min(0.1, rawDt);
    this.last = now;
    this.frameNo++;

    let dirty = false;
    if (this.intro < 1) {
      this.intro = Math.min(1, this.intro + Math.min(0.25, rawDt) / 2.4);
      dirty = true;
    }

    for (const key of ["hero", "build", "px", "py"] as const) {
      const sp = this.springs[key];
      if (this.opts.reducedMotion) {
        sp.x = this.target[key];
        sp.v = 0;
      } else if (sp.step(this.target[key], dt)) {
        dirty = true;
      }
    }

    const continuous = !this.opts.reducedMotion && !this.lowPower;
    if (!this.opts.reducedMotion) {
      this.clock += dt;
    }

    if (dirty || this.high || this.frameNo % 2 !== 1) {
      try {
        const appliedDirty = this.apply(dt);
        dirty ||= appliedDirty;
        if (this.high && this.frameNo % (dirty ? 2 : 4) === 0) {
          this.renderer.shadowMap.needsUpdate = true;
        }
        this.renderer.render(this.scene, this.camera);
      } catch (err) {
        this.opts.onError?.(err);
        return;
      }
      if (rawDt < 0.25) {
        this.adaptResolution(rawDt);
      }
    }

    if (dirty || continuous) {
      this.requestFrame();
    }
  };

  private adaptResolution(dt: number) {
    if (dt > 1 / 48) this.perfSlow++;
    if (++this.perfN < 40) return;
    const ratio = this.perfSlow / this.perfN;
    this.perfSlow = 0;
    this.perfN = 0;
    // Step resolution down gently when frames run slow, never below 1x
    // (sub-1x is what made the scene blurry), and step back up once the
    // GPU keeps up again.
    if (ratio >= 0.5) {
      if (this.dpr > 1.01) {
        this.setDpr(Math.max(1, this.dpr * 0.85));
      } else {
        this.lowPower = true;
      }
    } else if (ratio <= 0.1 && this.dpr < this.maxDpr - 0.01) {
      this.setDpr(Math.min(this.maxDpr, this.dpr * 1.15));
    }
  }

  private setDpr(dpr: number) {
    this.dpr = dpr;
    this.renderer.setPixelRatio(dpr);
    this.renderer.setSize(this.width, this.height, false);
  }

  private fitDistance(
    az: number,
    elev: number,
    target: THREE.Vector3,
    points: THREE.Vector3[]
  ) {
    const { right, up, back, v } = this.tmp;
    back.set(
      Math.cos(elev) * Math.sin(az),
      Math.sin(elev),
      Math.cos(elev) * Math.cos(az)
    );
    right.set(Math.cos(az), 0, -Math.sin(az));
    up.crossVectors(back, right);

    const tanHalfFov = Math.tan((this.camera.fov * Math.PI) / 360) * 0.94;
    const tanHalfH = tanHalfFov * this.camera.aspect;
    let maxDist = 0;
    for (const pt of points) {
      v.subVectors(pt, target);
      const depth = v.dot(back);
      maxDist = Math.max(
        maxDist,
        depth + Math.abs(v.dot(right)) / tanHalfH,
        depth + Math.abs(v.dot(up)) / tanHalfFov
      );
    }
    return maxDist;
  }

  private updateMood(buildProgress: number) {
    let idx = 0;
    while (
      idx < MOOD_KEYFRAMES.length - 2 &&
      buildProgress > MOOD_KEYFRAMES[idx + 1].at
    ) {
      idx++;
    }
    const k0 = MOOD_KEYFRAMES[idx];
    const k1 = MOOD_KEYFRAMES[idx + 1];
    const f = smoothstep01(
      clamp01((buildProgress - k0.at) / (k1.at - k0.at))
    );
    const m = this.mood;
    m.top.copy(k0.topC).lerp(k1.topC, f);
    m.horizon.copy(k0.horizonC).lerp(k1.horizonC, f);
    m.sun.copy(k0.sunC).lerp(k1.sunC, f);
    m.sunI = lerp(k0.sunI, k1.sunI, f);
    m.hemi = lerp(k0.hemi, k1.hemi, f);
    m.elev = lerp(k0.elev, k1.elev, f);
    m.az = lerp(k0.az, k1.az, f);
    m.glow = lerp(k0.glow, k1.glow, f);
    m.exposure = lerp(k0.exposure, k1.exposure, f);
  }

  private apply(_dt: number) {
    const build = this.springs.build.x;
    const hero = this.springs.hero.x;
    const clk = this.clock;

    // 1. Blueprint CAD wireframe draw-in on load
    const drawCount = Math.floor(
      easeInOutCubic(this.intro) * this.lineVertexCount
    );
    this.lines.geometry.setDrawRange(0, drawCount - (drawCount % 2));

    // Continuous scroll progression from Hero (0 -> 0.08) through Stages 01..06 (0.06 -> 1.0)
    const effectiveBuild = Math.max(build, hero * 0.08);

    const pApp = rangeProgress(effectiveBuild, STAGE_RANGES.approvals);
    const pStruct = rangeProgress(effectiveBuild, STAGE_RANGES.structure);
    const pFin = rangeProgress(effectiveBuild, STAGE_RANGES.finishes);
    const pHand = rangeProgress(effectiveBuild, STAGE_RANGES.handover);

    // Blueprint wireframe opacity (strong in Hero & Stage 01, fades subtly as solid optics & holograms complete)
    const baseWireOpacity =
      lerp(0.95, 0.48, pStruct) * lerp(1, 0.25, smoothstep01(pFin));
    this.lineMat.opacity = this.realHeadsetLoaded
      ? baseWireOpacity * 0.28
      : baseWireOpacity;

    this.boundaryMat.opacity =
      0.75 * easeOutCubic(clamp01(effectiveBuild * 4));

    // Update all instanced batches (turntable, pedestal, gantries)
    for (const b of this.batches) {
      b.update(effectiveBuild);
    }

    // Gentle floating levitation of the Quest 3S headset
    const floatOffset = this.opts.reducedMotion
      ? 0
      : Math.sin(clk * 1.3) * 0.14;

    if (this.realHeadsetLoaded) {
      this.realHeadsetRoot.visible = true;
      this.realHeadsetRoot.position.y = 5.3 + floatOffset;
      this.realHeadsetRoot.rotation.z = this.opts.reducedMotion
        ? 0
        : Math.sin(clk * 0.7) * 0.022;
      this.realHeadsetRoot.rotation.y = this.opts.reducedMotion
        ? 0
        : Math.cos(clk * 0.55) * 0.04;

      // Animate exploded engineering sub-assemblies -> zero-tolerance lock across Stages 01..03
      // In the Hero (effectiveBuild < 0.08), show a dramatic 48% architectural exploded cutaway that expands in Stage 01 and locks to 0% by Stage 03
      const heroExplodeScale = lerp(
        0.48,
        0.85,
        smoothstep01(clamp01(effectiveBuild / 0.12))
      );
      for (const sub of this.realSubAssemblies) {
        const lockProg = easeInOutCubic(
          rangeProgress(effectiveBuild, [sub.t0, sub.t1])
        );
        const explodeFactor = (1 - lockProg) * heroExplodeScale;
        sub.node.position
          .copy(sub.basePos)
          .addScaledVector(sub.explodeOffset, explodeFactor);
      }
    } else {
      this.realHeadsetRoot.visible = false;
    }

    // 4. Precision Calibration Gantries (active during Stages 02-04, retract in Stage 05)
    const gantryVis =
      smoothstep01(rangeProgress(effectiveBuild, [0.12, 0.22])) *
      (1 - smoothstep01(rangeProgress(effectiveBuild, [0.74, 0.85])));
    this.leftGantry.visible = gantryVis > 0.01;
    this.rightGantry.visible = gantryVis > 0.01;
    this.leftGantry.scale.y = Math.max(0.001, gantryVis);
    this.rightGantry.scale.y = Math.max(0.001, gantryVis);
    if (gantryVis > 0.01) {
      this.leftGantryArm.rotation.z = Math.sin(clk * 1.6) * 0.22;
      this.leftGantryArm.rotation.y = Math.cos(clk * 0.9) * 0.35;
      this.rightGantryArm.rotation.z = -Math.sin(clk * 1.6) * 0.22;
      this.rightGantryArm.rotation.y = -Math.cos(clk * 0.9) * 0.35;
    }

    // 5. Waveguide Projection Beams & Floating Spatial UI Screens (Stage 04: [0.48, 0.72])
    const holoAppear = easeOutCubic(
      rangeProgress(effectiveBuild, [0.46, 0.72])
    );
    this.beamMat.opacity = 0.16 * holoAppear;
    this.beamLeft.visible = holoAppear > 0.01;
    this.beamRight.visible = holoAppear > 0.01;

    this.hudScreensGroup.visible = holoAppear > 0.01;
    const hudScale = Math.max(0.001, holoAppear);
    this.hudScreensGroup.scale.setScalar(hudScale);
    this.hudScreensGroup.position.y = (1 - holoAppear) * -1.2;

    // 6. Meiporul 3D Polyhedron Core, Double-Helix & Gyroscopic Knowledge Rings (Stage 05: [0.64, 0.88])
    const coreAppear = easeOutCubic(
      rangeProgress(effectiveBuild, [0.6, 0.86])
    );
    this.holoCore.visible = coreAppear > 0.01;
    this.holoCore.scale.setScalar(Math.max(0.001, coreAppear));
    this.holoCore.rotation.y = clk * 0.45 + effectiveBuild * Math.PI * 2;
    this.holoCore.rotation.x = clk * 0.28;

    this.helixGroup.visible = coreAppear > 0.01;
    this.helixGroup.scale.setScalar(Math.max(0.001, coreAppear));
    this.helixGroup.rotation.y = -clk * 0.35 - effectiveBuild * Math.PI;

    const ringAppear = easeOutCubic(
      rangeProgress(effectiveBuild, [0.64, 0.9])
    );
    for (const [idx, rGrp] of [
      this.gyroRing1,
      this.gyroRing2,
      this.gyroRing3,
    ].entries()) {
      rGrp.visible = ringAppear > 0.01;
      rGrp.scale.setScalar(Math.max(0.001, ringAppear));
      const dir = idx % 2 === 0 ? 1 : -1;
      rGrp.rotation.x =
        0.55 + idx * 0.42 + (clk * 0.22 + effectiveBuild * 1.8) * dir;
      rGrp.rotation.y = (clk * 0.31 + effectiveBuild * 2.2) * -dir;
      rGrp.rotation.z = idx * 0.3 + Math.sin(clk * 0.4 + idx) * 0.25;
    }

    // 7. Photon Knowledge Particles
    if (this.dust) {
      const dustVis = Math.max(0.35, coreAppear);
      const dustMat = this.dust.material as THREE.PointsMaterial;
      dustMat.opacity = 0.55 * dustVis;
      this.dust.visible = dustVis > 0.01;
      const posAttr = this.dust.geometry.getAttribute("position");
      const seeds = this.dustSeeds;
      for (let i = 0; i < posAttr.count; i++) {
        const py =
          1.0 + ((seeds[i * 3 + 1] + clk * (0.28 + (i % 7) * 0.04)) % 8.5);
        const orbitAngle = clk * 0.18 + (i % 12) * 0.52;
        const px = seeds[i * 3] + Math.cos(orbitAngle) * 0.45;
        const pz = seeds[i * 3 + 2] + Math.sin(orbitAngle) * 0.45;
        posAttr.setXYZ(i, px, py, pz);
      }
      posAttr.needsUpdate = true;
    }

    // Beacon pulse
    this.beaconMat.color
      .setRGB(1, 0.35, 0.2)
      .multiplyScalar(Math.sin(clk * 3.2) > 0.4 ? 2.2 : 0.4);

    // 8. Mood, Atmosphere & Dusk Illumination
    this.updateMood(effectiveBuild);
    const m = this.mood;
    this.renderer.toneMappingExposure = m.exposure;
    this.sun.color.copy(m.sun);
    this.sun.intensity = m.sunI;
    this.hemi.intensity = m.hemi * 1.4;
    this.skyMat.uniforms.top.value.copy(m.top);
    this.skyMat.uniforms.horizon.value.copy(m.horizon);
    this.skyMat.uniforms.sunColor.value.copy(m.sun);
    this.skyMat.uniforms.glow.value = m.glow;

    const sunDir = this.skyMat.uniforms.sunDir.value as THREE.Vector3;
    sunDir.set(
      Math.sin(m.az) * Math.cos(m.elev),
      Math.sin(m.elev),
      Math.cos(m.az) * Math.cos(m.elev)
    );

    this.fog.color.copy(m.horizon);
    this.lampMat.color
      .set("#ffd9a0")
      .multiplyScalar(lerp(0.6, 1.8, Math.max(pApp, pHand)));
    this.litMat.color
      .set("#ffc98a")
      .multiplyScalar(lerp(0.9, 1.8, Math.max(pStruct, pHand)));
    this.glowMat.opacity = 0.18 + 0.18 * pFin + 0.28 * pHand;

    // 9. Scroll-Driven Camera Orbit & Elevation Path
    const heroS = smoothstep01(clamp01(hero));
    const motionMul = +!this.opts.reducedMotion;
    let camAz =
      lerp(-0.52, -0.28, heroS) +
      smoothstep01(build) * 1.25 +
      this.springs.px.x * 0.08 +
      Math.sin(clk * 0.11) * 0.04 * motionMul;
    let camElev =
      lerp(0.48, 0.28, heroS) -
      lerp(0, 0.16, smoothstep01(clamp01(build * 1.3))) +
      this.springs.py.x * 0.04 +
      Math.sin(clk * 0.08 + 1) * 0.018 * motionMul;
    let zoomMul = lerp(0.96, 0.92, heroS) + pHand * 0.06;

    if (this.opts.reducedMotion) {
      camAz = 0.28;
      camElev = 0.25;
      zoomMul = 0.95;
    }

    const c = this.center;
    const dist = this.fitDistance(camAz, camElev, c, this.corners) * zoomMul;

    this.camera.position.set(
      c.x + dist * Math.cos(camElev) * Math.sin(camAz),
      c.y + dist * Math.sin(camElev),
      c.z + dist * Math.cos(camElev) * Math.cos(camAz)
    );
    this.camera.lookAt(c);
    this.fog.near = dist * 1.25;
    this.fog.far = dist * 3.8;
    this.sun.position.copy(c).addScaledVector(sunDir, 75);
    this.sun.target.position.copy(c);

    return false;
  }
}

export function isIntegratedGPU() {
  try {
    const gl = document.createElement("canvas").getContext("webgl");
    if (!gl) return true;
    const ext = gl.getExtension("WEBGL_debug_renderer_info");
    const rendererStr = String(
      gl.getParameter(ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER)
    );
    gl.getExtension("WEBGL_lose_context")?.loseContext();
    return !/nvidia|geforce|quadro|rtx|gtx|radeon rx|radeon pro/i.test(
      rendererStr
    );
  } catch {
    return true;
  }
}

export function supportsWebGL() {
  try {
    const c = document.createElement("canvas");
    return !!(
      typeof window !== "undefined" &&
      window.WebGLRenderingContext &&
      (c.getContext("webgl2") || c.getContext("webgl"))
    );
  } catch {
    return false;
  }
}
