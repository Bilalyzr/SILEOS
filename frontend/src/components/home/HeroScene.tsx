import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

/**
 * Signature 3D hero for the home page — a slowly turning "learning
 * constellation": an icosahedron core with orbiting knowledge nodes, lit in
 * the existing brand palette (orange/amber on the dark canvas). Pure
 * geometry, no model assets to load. Follows the SashaAvatarStage pattern:
 * vanilla three.js on a canvas ref, WebGL failure tolerated, pixel ratio
 * capped, everything disposed on unmount. Respects prefers-reduced-motion
 * (renders a single static frame) and pauses when offscreen or hidden.
 */
export function HeroScene({ className = "" }: { className?: string }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    } catch {
      setFailed(true);
      return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    camera.position.set(0, 0.4, 7.4);

    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.25;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8));

    // Brand lighting — same orange/amber key rig as the AI avatar stage.
    scene.add(new THREE.HemisphereLight(0xdbeafe, 0x111827, 1.6));
    const key = new THREE.DirectionalLight(0xffffff, 2.6);
    key.position.set(4, 6, 6);
    scene.add(key);
    const orange = new THREE.DirectionalLight(0xfb923c, 2.4);
    orange.position.set(-5, 2, 3);
    scene.add(orange);
    const amber = new THREE.PointLight(0xfbbf24, 14, 12);
    amber.position.set(2.5, -2, 3);
    scene.add(amber);

    const brand = 0xff751f; // primary-500 — existing brand orange

    const core = new THREE.Mesh(
      new THREE.IcosahedronGeometry(1.55, 1),
      new THREE.MeshStandardMaterial({
        color: brand,
        roughness: 0.32,
        metalness: 0.25,
        flatShading: true,
      }),
    );
    scene.add(core);

    const shell = new THREE.Mesh(
      new THREE.IcosahedronGeometry(2.15, 1),
      new THREE.MeshBasicMaterial({
        color: brand,
        wireframe: true,
        transparent: true,
        opacity: 0.18,
      }),
    );
    scene.add(shell);

    // Orbiting knowledge nodes on two tilted rings.
    const nodes: THREE.Mesh[] = [];
    const orbits: { radius: number; speed: number; tilt: number; phase: number }[] = [
      { radius: 2.9, speed: 0.32, tilt: Math.PI / 3.1, phase: 0 },
      { radius: 3.35, speed: -0.22, tilt: Math.PI / 1.9, phase: 2.1 },
    ];
    const nodeGeo = new THREE.SphereGeometry(0.11, 16, 16);
    const nodeMat = new THREE.MeshStandardMaterial({
      color: 0xfbbf24,
      roughness: 0.25,
      metalness: 0.4,
      emissive: brand,
      emissiveIntensity: 0.35,
    });
    for (const orbit of orbits) {
      for (let i = 0; i < 6; i++) {
        const node = new THREE.Mesh(nodeGeo, nodeMat);
        node.userData.orbit = { ...orbit, offset: (i / 6) * Math.PI * 2 };
        nodes.push(node);
        scene.add(node);
      }
    }

    const platformMat = new THREE.MeshBasicMaterial({
      color: brand,
      transparent: true,
      opacity: 0.22,
      side: THREE.DoubleSide,
    });
    const platform = new THREE.Mesh(new THREE.RingGeometry(2.0, 2.07, 72), platformMat);
    platform.rotation.x = Math.PI / 2;
    platform.position.y = -2.5;
    scene.add(platform);

    mount.appendChild(renderer.domElement);
    renderer.domElement.setAttribute("aria-hidden", "true");
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.display = "block";

    const resize = () => {
      const w = mount.clientWidth || 1;
      const h = mount.clientHeight || 1;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(mount);

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let visible = true;
    const io = new IntersectionObserver((es) => { visible = es[0].isIntersecting; });
    io.observe(mount);

    let raf = 0;
    let disposed = false;

    const placeNodes = (t: number) => {
      for (const node of nodes) {
        const o = node.userData.orbit as (typeof orbits)[number] & { offset: number };
        const a = o.phase + o.offset + t * o.speed;
        const x = Math.cos(a) * o.radius;
        const z = Math.sin(a) * o.radius;
        const y = Math.sin(a) * Math.sin(o.tilt) * o.radius * 0.5;
        node.position.set(x, y, z);
      }
    };

    const renderFrame = (t: number) => {
      core.rotation.y = t * 0.18;
      core.rotation.x = Math.sin(t * 0.12) * 0.22;
      shell.rotation.y = -t * 0.1;
      shell.rotation.z = t * 0.05;
      placeNodes(t);
      renderer.render(scene, camera);
    };

    if (reduced) {
      renderFrame(1.4); // one static, composed frame
    } else {
      const t0 = performance.now();
      const loop = () => {
        if (disposed) return;
        if (visible && !document.hidden) renderFrame((performance.now() - t0) / 1000);
        raf = requestAnimationFrame(loop);
      };
      raf = requestAnimationFrame(loop);
    }

    return () => {
      disposed = true;
      cancelAnimationFrame(raf);
      observer.disconnect();
      io.disconnect();
      nodeGeo.dispose();
      nodeMat.dispose();
      shell.geometry.dispose();
      (shell.material as THREE.Material).dispose();
      core.geometry.dispose();
      (core.material as THREE.Material).dispose();
      platform.geometry.dispose();
      platformMat.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  if (failed) return null;
  return <div ref={mountRef} className={className} aria-hidden="true" />;
}
