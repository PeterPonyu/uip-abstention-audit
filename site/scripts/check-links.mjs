import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { join, dirname, extname } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const siteDir = join(root, "_site");
const prefix = "/uip-abstention-audit";
const required = [
  "/",
  "/protocol/",
  "/potentials/",
  "/error/",
  "/mechanism/",
  "/controls/",
  "/reproduce/",
  "/cite/",
];

function resolvePage(route) {
  const rel = route.replace(/^\//, "");
  const candidates = [
    join(siteDir, rel, "index.html"),
    join(siteDir, rel.replace(/\/$/, "") + ".html"),
    join(siteDir, rel),
  ];
  return candidates.find((p) => existsSync(p));
}

const missing = required.filter((route) => !resolvePage(route));
if (missing.length) {
  console.error("Missing routes:", missing.join(", "));
  process.exit(1);
}

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if (extname(p) === ".html") out.push(p);
  }
  return out;
}

const hrefRe = /href="([^"]+)"/g;
const broken = [];
for (const file of walk(siteDir)) {
  const html = readFileSync(file, "utf8");
  for (const match of html.matchAll(hrefRe)) {
    const href = match[1];
    if (href.startsWith("http") || href.startsWith("mailto:") || href.startsWith("#")) continue;
    let path = href;
    if (path.startsWith(prefix)) path = path.slice(prefix.length) || "/";
    if (path.startsWith("/")) {
      const target = path.endsWith("/") || path.split("/").pop().includes(".")
        ? path
        : path + "/";
      if (path.includes(".")) {
        const asset = join(siteDir, path.replace(/^\//, ""));
        if (!existsSync(asset)) broken.push(`${file} -> ${href}`);
      } else if (!resolvePage(target) && !resolvePage(path)) {
        broken.push(`${file} -> ${href}`);
      }
    } else {
      const asset = join(dirname(file), path);
      if (!existsSync(asset)) broken.push(`${file} -> ${href}`);
    }
  }
}

if (broken.length) {
  console.error("Broken in-site hrefs:");
  for (const row of broken) console.error(row);
  process.exit(1);
}

const cssRoots = walk(siteDir).flatMap((file) => {
  const html = readFileSync(file, "utf8");
  return [...html.matchAll(/(?:href|src)="(\/css\/[^"]+)"/g)].map((m) => `${file}: ${m[1]}`);
});
if (cssRoots.length) {
  console.error("Unprefixed /css/ roots:", cssRoots.join("\n"));
  process.exit(1);
}

console.log("link-check ok");
