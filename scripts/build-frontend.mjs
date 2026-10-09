import { cp, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import * as sass from "sass";

const root = resolve(import.meta.dirname, "..");
const scss = resolve(root, "frontend/admin/assets/cms.scss");
const css = resolve(root, "frontend/admin/assets/cms.css");
const grapesSource = resolve(root, "node_modules/grapesjs/dist");
const grapesTarget = resolve(root, "frontend/admin/assets/vendor/grapesjs");
const runtimeSource = resolve(root, "frontend/shared/cms-runtime.js");

const result = sass.compile(scss, { style: "compressed", sourceMap: false });
await mkdir(dirname(css), { recursive: true });
await writeFile(css, result.css);
await mkdir(grapesTarget, { recursive: true });
await cp(grapesSource, grapesTarget, { recursive: true, force: true });
for (const site of ["uhrbv", "ukrwerkspot"]) {
  await cp(runtimeSource, resolve(root, `frontend/${site}/preview/assets/cms-runtime.js`), { force: true });
}

console.log("Frontend assets built.");
