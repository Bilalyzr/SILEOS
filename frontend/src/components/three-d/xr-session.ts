import * as THREE from "three";

/** One session owner; cleanup also covers unmounts while permission is pending. */
export function createXRSession(
  renderer: THREE.WebGLRenderer,
  scene: THREE.Scene,
  camera: THREE.PerspectiveCamera,
  content: THREE.Group,
  onMessage: (message: string) => void,
  onActive: (active: boolean) => void,
  onAnchor?: (id: string) => void,
) {
  let disposed = false,
    session: any = null,
    hitSource: any = null,
    starting = false;
  let oldPosition = new THREE.Vector3(),
    oldScale = new THREE.Vector3(),
    near = camera.near,
    far = camera.far;
  let background = scene.background;
  const reticle = new THREE.Mesh(
    new THREE.RingGeometry(0.07, 0.09, 32).rotateX(-Math.PI / 2),
    new THREE.MeshBasicMaterial({ color: 0xff751f }),
  );
  reticle.matrixAutoUpdate = false;
  reticle.visible = false;
  scene.add(reticle);
  renderer.xr.enabled = true;
  const controllers = [0, 1].map((index) => {
    const controller = renderer.xr.getController(index);
    const line = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(),
        new THREE.Vector3(0, 0, -3),
      ]),
      new THREE.LineBasicMaterial({ color: 0xff751f }),
    );
    controller.add(line);
    scene.add(controller);
    const select = () => {
      const ray = new THREE.Raycaster();
      ray.ray.origin.setFromMatrixPosition(controller.matrixWorld);
      ray.ray.direction
        .set(0, 0, -1)
        .transformDirection(controller.matrixWorld);
      const marker = ray
        .intersectObject(content, true)
        .find((hit) => hit.object.userData.anchorId);
      if (marker) onAnchor?.(marker.object.userData.anchorId);
    };
    controller.addEventListener("select", select);
    return { controller, line, select };
  });
  function restore() {
    hitSource?.cancel();
    hitSource = null;
    session = null;
    reticle.visible = false;
    content.position.copy(oldPosition);
    content.scale.copy(oldScale);
    scene.background = background;
    camera.near = near;
    camera.far = far;
    camera.updateProjectionMatrix();
    if (!disposed) {
      onActive(false);
      onMessage("Screen mode restored.");
    }
  }
  async function toggle(mode: "immersive-ar" | "immersive-vr") {
    if (session) {
      await session.end();
      return;
    }
    if (starting || disposed) return;
    starting = true;
    try {
      const xr = (navigator as any).xr;
      if (!window.isSecureContext || !xr)
        throw new Error(
          "Use HTTPS and a WebXR-capable device. Screen mode remains available.",
        );
      const created = await xr.requestSession(
        mode,
        mode === "immersive-ar"
          ? {
              requiredFeatures: ["hit-test"],
              optionalFeatures: ["dom-overlay"],
              domOverlay: { root: document.body },
            }
          : {
              optionalFeatures: ["local-floor", "dom-overlay"],
              domOverlay: { root: document.body },
            },
      );
      if (disposed) {
        await created.end();
        return;
      }
      session = created;
      oldPosition = content.position.clone();
      oldScale = content.scale.clone();
      background = scene.background;
      near = camera.near;
      far = camera.far;
      created.addEventListener("end", restore, { once: true });
      const size = new THREE.Box3()
        .setFromObject(content)
        .getSize(new THREE.Vector3());
      content.scale.setScalar(0.8 / (Math.max(size.x, size.y, size.z) || 1));
      content.position.set(0, 0, -1.5);
      camera.near = 0.01;
      camera.far = 100;
      camera.updateProjectionMatrix();
      renderer.xr.setReferenceSpaceType("local");
      if (mode === "immersive-ar") {
        scene.background = null;
        hitSource = await created.requestHitTestSource({
          space: await created.requestReferenceSpace("viewer"),
        });
        created.addEventListener("select", () => {
          if (reticle.visible) {
            content.position.setFromMatrixPosition(reticle.matrix);
            content.position.y += size.y * content.scale.y * 0.5;
          }
        });
      }
      await renderer.xr.setSession(created);
      if (disposed) {
        await created.end();
        return;
      }
      onActive(true);
      onMessage(
        mode === "immersive-ar"
          ? "Move the device to find a surface; tap to place the model."
          : "VR ready. Inspect the model with your headset.",
      );
    } catch (e: any) {
      if (session) {
        try {
          await session.end();
        } catch {
          restore();
        }
      }
      if (!disposed)
        onMessage(e.message || "Could not start XR. Use screen mode.");
    } finally {
      starting = false;
    }
  }
  return {
    toggle,
    frame(frame: any) {
      if (!frame || !hitSource) return;
      const ref = renderer.xr.getReferenceSpace();
      const hits = frame.getHitTestResults(hitSource);
      reticle.visible = hits.length > 0;
      if (hits.length && ref) {
        const pose = hits[0].getPose(ref);
        if (pose) reticle.matrix.fromArray(pose.transform.matrix);
      }
    },
    dispose() {
      disposed = true;
      hitSource?.cancel();
      hitSource = null;
      session?.end().catch(() => {});
      scene.remove(reticle);
      reticle.geometry.dispose();
      reticle.material.dispose();
      controllers.forEach(({ controller, line, select }) => {
        controller.removeEventListener("select", select);
        controller.remove(line);
        scene.remove(controller);
        line.geometry.dispose();
        line.material.dispose();
      });
    },
  };
}
