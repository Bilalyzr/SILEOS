/* Render each real bundled GLB under each deployed CSP (including blob loading). */
const fs = require('node:fs'), path = require('node:path'), http = require('node:http');
const { execFileSync } = require('node:child_process');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = process.cwd(), modelRoot = path.join(root, 'backend/seed_packs/models');
const threeRoot = path.join(root, 'frontend/node_modules/three');
const catalog = JSON.parse(fs.readFileSync(path.join(modelRoot, 'catalog.json')));
const configs = ['nginx/conf.d/default.conf', 'nginx/conf.d/default.production.conf', 'deploy/nginx/snippets/security-headers.conf'];
const policies = configs.map(file => {
  const source = process.argv.includes('--baseline') ? execFileSync('git', ['show', 'HEAD:' + file], { encoding: 'utf8' }) : fs.readFileSync(file, 'utf8');
  return source.match(/add_header Content-Security-Policy "(default-src[^"\r\n]+)"/)[1];
});
const server = http.createServer((req,res) => {
  const url = new URL(req.url,'http://local');
  if (url.pathname === '/loader.js') {
    const esbuild = require(path.join(root,'frontend/node_modules/esbuild'));
    res.setHeader('Content-Type','text/javascript');
    res.end(esbuild.transformSync(fs.readFileSync(path.join(root,'frontend/src/components/three-d/load-glb.ts'),'utf8'),{loader:'ts',format:'esm'}).code);
    return;
  }
  if (url.pathname === '/') {
    const model = catalog.models[Number(url.searchParams.get('model'))];
    res.setHeader('Content-Type','text/html');
    res.setHeader('Content-Security-Policy', policies[Number(url.searchParams.get('policy'))]);
    res.end(`<!doctype html><meta charset="utf-8"><title>Model release check</title>
      <style>body{margin:0;background:#fff8f1}canvas{display:block}</style>
      <script type="importmap">{"imports":{"three":"/three/build/three.module.js","three/":"/three/"}}</script>
      <script type="module">
      import * as THREE from 'three';
      import {GLTFLoader} from '/three/examples/jsm/loaders/GLTFLoader.js';
      import {loadGlb} from '/loader.js';
      try {
        const response = await fetch('/models/${model.file}');
        ${process.argv.includes('--baseline') ? `const blob = URL.createObjectURL(await response.blob()); const model = await new GLTFLoader().loadAsync(blob);` : `const model = await loadGlb(await response.arrayBuffer());`}
        const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(900,700);
        document.body.append(renderer.domElement);
        const scene=new THREE.Scene();scene.background=new THREE.Color('#fff8f1');
        scene.add(new THREE.HemisphereLight(0xffffff,0x664422,3));scene.add(model.scene);
        const box=new THREE.Box3().setFromObject(model.scene),center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3()).length()||1;
        model.scene.position.sub(center);
        const camera=new THREE.PerspectiveCamera(50,900/700,size/1000,size*100);
        camera.position.set(size*.7,size*.5,size*1.4);camera.lookAt(0,0,0);
        renderer.render(scene,camera);
        window.result={calls:renderer.info.render.calls,triangles:renderer.info.render.triangles};
      } catch(error) { window.result={error:error.message}; }
      </script>`);return;
  }
  const mount = url.pathname.startsWith('/models/') ? modelRoot : threeRoot;
  const rel = url.pathname.replace(/^\/(models|three)\//,'');
  const file = path.resolve(mount,rel);
  if (!file.startsWith(mount+path.sep) || !fs.existsSync(file)) {res.writeHead(404);res.end();return;}
  res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':'model/gltf-binary');fs.createReadStream(file).pipe(res);
});
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{}),args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const results=[];const out=path.resolve('.toolchains/release-audit/models');fs.mkdirSync(out,{recursive:true});
  try {
    for(let policy=0;policy<policies.length;policy++) for(let model=0;model<catalog.models.length;model++) {
      const page=await browser.newPage({viewport:{width:900,height:700}});
      await page.goto(`http://127.0.0.1:${server.address().port}/?policy=${policy}&model=${model}`);
      await page.waitForFunction(()=>window.result,null,{timeout:15000});
      const result=await page.evaluate(()=>window.result);
      results.push({policy:configs[policy],title:catalog.models[model].title,...result});
      if(!result.error&&policy===0)await page.screenshot({path:path.join(out,`model-${model}.png`)});
      await page.close();
    }
  } finally {await browser.close();server.close();}
  fs.writeFileSync(path.join(out,process.argv.includes('--baseline')?'before.json':'after.json'),JSON.stringify(results,null,2));
  console.log(JSON.stringify({cases:results.length,failed:results.filter(r=>r.error||!r.calls).length,results},null,2));
  process.exitCode=results.some(r=>r.error||!r.calls)?1:0;
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
