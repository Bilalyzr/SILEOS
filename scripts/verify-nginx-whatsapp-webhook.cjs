/* Verify that every shipped app-facing nginx config protects the public webhook. */
const fs = require("node:fs");

const route = "location = /api/v1/whatsapp/webhook {";
const configs = [
  {
    file: "deploy/nginx/conf.d/10-app.conf",
    count: 1,
    proxyPass: "proxy_pass http://$up_backend;",
    forwardedProto: "proxy_set_header X-Forwarded-Proto $fwd_proto;",
  },
  {
    file: "nginx/conf.d.local/default.conf",
    count: 1,
    proxyPass: "proxy_pass http://backend:8000;",
    forwardedProto: "proxy_set_header X-Forwarded-Proto $scheme;",
  },
  {
    file: "nginx/conf.d/default.conf",
    count: 2,
    proxyPass: "proxy_pass http://backend:8000;",
    forwardedProto: "proxy_set_header X-Forwarded-Proto $scheme;",
  },
  {
    file: "nginx/conf.d/default.production.conf",
    count: 1,
    proxyPass: "proxy_pass http://127.0.0.1:8000;",
    forwardedProto: "proxy_set_header X-Forwarded-Proto $scheme;",
  },
];

function exactLocationBlocks(source) {
  const blocks = [];
  let offset = 0;
  while (true) {
    const start = source.indexOf(route, offset);
    if (start === -1) break;
    let depth = 0;
    let end = start;
    for (; end < source.length; end += 1) {
      if (source[end] === "{") depth += 1;
      if (source[end] === "}") {
        depth -= 1;
        if (depth === 0) {
          end += 1;
          break;
        }
      }
    }
    if (depth !== 0) throw new Error(`Unbalanced webhook location near byte ${start}`);
    blocks.push(source.slice(start, end));
    offset = end;
  }
  return blocks;
}

const requiredDirectives = [
  "client_max_body_size 1M;",
  "proxy_set_header Host $host;",
  "proxy_set_header X-Real-IP $remote_addr;",
  "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
  "proxy_set_header X-Hub-Signature-256 $http_x_hub_signature_256;",
  "proxy_read_timeout 300s;",
  "proxy_send_timeout 300s;",
];

const failures = [];
let checked = 0;
for (const config of configs) {
  const source = fs.readFileSync(config.file, "utf8");
  const blocks = exactLocationBlocks(source);
  if (blocks.length !== config.count) {
    failures.push(`${config.file}: expected ${config.count} exact webhook location(s), found ${blocks.length}`);
  }
  for (const [index, block] of blocks.entries()) {
    checked += 1;
    for (const directive of [
      ...requiredDirectives,
      config.proxyPass,
      config.forwardedProto,
    ]) {
      if (!block.includes(directive)) {
        failures.push(`${config.file} webhook block ${index + 1}: missing ${directive}`);
      }
    }
  }
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exitCode = 1;
} else {
  console.log(`Verified ${checked} exact WhatsApp webhook locations across ${configs.length} nginx configs.`);
}
