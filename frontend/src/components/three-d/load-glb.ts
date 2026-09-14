import { LoadingManager, TextureLoader } from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

/** Decode trusted GLB bytes without fetching blob: URLs. The deployed CSP allows
 * data images but deliberately does not allow blob network requests. */
export function loadGlb(data: ArrayBuffer) {
  const manager = new LoadingManager();
  manager.addHandler(/^data:image\//i, new TextureLoader(manager));
  const loader = new GLTFLoader(manager);
  loader.register(parser => ({
    name: 'SASHA_EMBEDDED_TEXTURES',
    async beforeRoot() {
      if (!Array.isArray(parser.json.scenes) || !parser.json.scenes.length) {
        throw new Error('This model has no valid scene. Re-export it as a complete GLB.');
      }
      await Promise.all((parser.json.images || []).map(async (image: {bufferView?: number; uri?: string; mimeType?: string}) => {
        if (image.bufferView === undefined) return;
        if (!/^image\/(png|jpeg|webp|avif)$/.test(image.mimeType || '')) {
          throw new Error('Use embedded PNG, JPEG, WebP or AVIF model textures.');
        }
        const buffer = await parser.getDependency('bufferView', image.bufferView);
        const bytes = new Uint8Array(buffer);
        const chunks: string[] = [];
        for (let i = 0; i < bytes.length; i += 0x8000) {
          chunks.push(String.fromCharCode(...bytes.subarray(i, i + 0x8000)));
        }
        image.uri = `data:${image.mimeType};base64,${btoa(chunks.join(''))}`;
        delete image.bufferView;
      }));
    },
  }));
  return loader.parseAsync(data, '').then(result => {
    if (!result.scene) throw new Error('This model has no default scene. Re-export it as a complete GLB.');
    return result;
  });
}
