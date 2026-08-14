import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, extname } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const siteDir = join(root, "_site");
const forbidFile = join(root, "FORBIDDEN.txt");
const patterns = readFileSync(forbidFile, "utf8")
  .split("\n")
  .map((line) => line.trim())
  .filter((line) => line && !line.startsWith("#"));

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if ([".html", ".svg", ".json", ".txt", ".md", ".sha256"].includes(extname(p))) out.push(p);
  }
  return out;
}

const files = walk(siteDir);
const hits = [];
for (const file of files) {
  const text = readFileSync(file, "utf8");
  for (const pat of patterns) {
    if (text.includes(pat)) hits.push(`${file}: ${pat}`);
  }
}

if (hits.length) {
  console.error("LEAK SCAN FAIL");
  for (const hit of hits) console.error(hit);
  process.exit(1);
}
console.log(`leak-scan ok (${files.length} files, ${patterns.length} patterns)`);
