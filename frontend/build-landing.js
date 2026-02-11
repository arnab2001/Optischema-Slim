import { build } from "vite";
import { copyFile, mkdir, rm } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

async function main() {
  const root = process.cwd();
  const outDir = path.join(root, "dist");

  // Clean output to avoid mixing app assets with landing
  await rm(outDir, { recursive: true, force: true });

  // Build only the landing entry
  await build({
    configFile: path.join(root, "vite.config.ts"),
    build: {
      outDir: "dist",
      emptyOutDir: true,
      rollupOptions: {
        input: {
          landing: path.join(root, "landing.html"),
        },
      },
    },
  });

  // Promote landing to root index.html for GitHub Pages
  await copyFile(path.join(outDir, "landing.html"), path.join(outDir, "index.html"));

  // 404.html should match index for GitHub Pages
  await copyFile(path.join(outDir, "index.html"), path.join(outDir, "404.html"));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
