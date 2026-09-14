import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
export function offlinePlugin() {
  return {
    name: "sasha-offline",
    apply: "build",
    writeBundle(options) {
      const dir = options.dir || "dist";
      const list = ["/offline.html"];
      function scan(relative) {
        const root = path.join(dir, relative);
        if (!fs.existsSync(root)) return;
        for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
          const next = relative + "/" + entry.name;
          if (entry.isDirectory()) scan(next);
          else if (/\.(js|css|html|woff2?|ttf|json)$/.test(entry.name))
            list.push("/" + next);
        }
      }
      scan("assets");
      scan("labs/cbse");
      scan("design");
      const digest = createHash("sha256");
      for (const file of list)
        digest.update(fs.readFileSync(path.join(dir, file.slice(1))));
      const cache = "sasha-offline-" + digest.digest("hex").slice(0, 16);
      const worker = `const NAME=${JSON.stringify(cache)}, FILES=${JSON.stringify(list)};\nself.addEventListener('install',e=>e.waitUntil(caches.open(NAME).then(c=>c.addAll(FILES)).then(()=>self.skipWaiting())));\nself.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('sasha-offline-')&&k!==NAME).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));\nself.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(e.request.method!=='GET'||u.origin!==location.origin||!FILES.includes(u.pathname))return;e.respondWith(caches.open(NAME).then(c=>c.match(u.pathname).then(r=>r||fetch(e.request))));});`;
      fs.writeFileSync(path.join(dir, "offline-worker.js"), worker);
    },
  };
}
