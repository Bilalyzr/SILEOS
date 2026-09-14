/** Build reviewed local lab sources. No archive scripts are executed by this builder. */
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const frontend = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const source = path.join(frontend, "labs");
const output = path.join(frontend, "public/labs/cbse");
const check = process.argv.includes("--check");
const labs = JSON.parse(
  await fs.readFile(path.join(source, "catalog/labs.json"), "utf8"),
);
const expected = new Map();
const add = (target, bytes) => {
  if (expected.has(target)) throw new Error(`Duplicate output: ${target}`);
  expected.set(target, bytes);
};
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (c) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[c]);
// Every supplied page links back here. Ship a real static library, including
// when the labs are opened independently of the React application/API.
add(path.join(output, 'index.html'), Buffer.from(`<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sasha Virtual Labs</title><style>
body{margin:0;background:#fff8f1;color:#25201c;font:16px system-ui,sans-serif}main{max-width:1160px;margin:auto;padding:40px 24px}
header{padding:32px;border-radius:24px;background:linear-gradient(125deg,#ff751f,#ffce9f);margin-bottom:24px}
h1{font-size:clamp(30px,5vw,52px);margin:8px 0}nav{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
a{display:block;background:#fff;border:1px solid #e4cdb8;padding:22px;border-radius:18px;color:inherit;text-decoration:none}
a:hover,a:focus-visible{outline:3px solid #cf5000}small{color:#70503c}h2{font-size:20px}p{line-height:1.6}</style></head>
<body><main><header><small>SASHA INFINITY · INTERACTIVE LEARNING</small><h1>Sasha Virtual Labs</h1>
<p>${labs.length} supplied simulations. Choose an experiment, change its controls and explore. 3D requires WebGL; AR/VR also requires a compatible device and a secure connection.</p></header>
<nav aria-label="Experiments">${labs.map(l => `<a href="${escapeHtml(l.file)}"><small>${escapeHtml(l.subject)}</small><h2>${escapeHtml(l.title)}</h2><p>${escapeHtml(l.description || '')}</p></a>`).join('')}</nav>
</main></body></html>`));
for (const lab of labs) {
  if (!/^labs\/[a-z]+\/[a-z0-9-]+\.html$/.test(lab.file))
    throw new Error(`Invalid lab path: ${lab.file}`);
  const name = path.basename(lab.file, ".html");
  const directory = path.join(
    source,
    "simulations",
    path.dirname(lab.file).slice(5),
    name,
  );
  const html = await fs.readFile(path.join(directory, "view.html"));
  add(path.join(output, lab.file), html);
  for (const item of (await fs.readdir(directory)).sort()) {
    if (item === "view.html") continue;
    if (!/\.(js|css)$/.test(item))
      throw new Error(`Unexpected lab source: ${item}`);
    const bytes = await fs.readFile(path.join(directory, item));
    if (item.endsWith(".js"))
      new vm.Script(bytes.toString(), { filename: `${name}/${item}` });
    add(path.join(output, path.dirname(lab.file), name, item), bytes);
  }
}
for (const folder of ["runtime", "vendor"]) {
  for (const item of (await fs.readdir(path.join(source, folder))).sort()) {
    const bytes = await fs.readFile(path.join(source, folder, item));
    const target =
      item === "concept.html"
        ? path.join(output, item)
        : path.join(output, "assets", item);
    if (item.endsWith(".js"))
      new vm.Script(bytes.toString(), { filename: item });
    add(target, bytes);
  }
}
for (const [target, bytes] of expected) {
  if (!target.endsWith(".html")) continue;
  for (const match of bytes
    .toString()
    .matchAll(/(?:src|href)=["']([^"']+)["']/g)) {
    const url = match[1];
    if (/^(?:[a-z]+:|\/|#)/i.test(url)) continue;
    const asset = path.resolve(path.dirname(target), url.split(/[?#]/)[0]);
    if (!expected.has(asset))
      throw new Error(`Missing asset ${url} referenced by ${target}`);
  }
}
for (const [from, to] of [
  ["labs.json", "cbse_labs.json"],
  ["curriculum-ncert-2024.json", "cbse_curriculum_ncert_2024.json"],
]) {
  add(
    path.join(frontend, "../backend/seed_packs", to),
    await fs.readFile(path.join(source, "catalog", from)),
  );
}
const stale = [];
// Lab iframes share the product design without depending on the React bundle.
for (const name of ["astra-glass.css", "astra-tokens.css"]) {
  add(
    path.join(frontend, "public/design", name),
    await fs.readFile(path.join(frontend, "src/styles", name)),
  );
}
for (const [target, bytes] of expected) {
  const current = await fs.readFile(target).catch(() => null);
  if (current?.equals(bytes)) continue;
  if (check) stale.push(path.relative(frontend, target));
  else {
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.writeFile(target, bytes);
  }
}
if (stale.length)
  throw new Error(
    `Generated labs are stale. Run npm run labs:build.\n${stale.join("\n")}`,
  );
console.log(
  `${check ? "Verified" : "Built"} ${labs.length} labs, ${expected.size} files; syntax and local asset references checked.`,
);
