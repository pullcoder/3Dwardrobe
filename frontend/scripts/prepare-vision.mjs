import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const modelUrl =
  "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task";
const destination = `${root}public/mediapipe`;
const expectedHash =
  "5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1";
await mkdir(`${destination}/wasm`, { recursive: true });
await copyFile(
  `${root}node_modules/@mediapipe/tasks-vision/vision_bundle.cjs`,
  `${destination}/vision_bundle.js`,
);
for (const file of [
  "vision_wasm_internal.js",
  "vision_wasm_internal.wasm",
  "vision_wasm_nosimd_internal.js",
  "vision_wasm_nosimd_internal.wasm",
  "vision_wasm_module_internal.js",
  "vision_wasm_module_internal.wasm",
]) {
  await copyFile(
    `${root}node_modules/@mediapipe/tasks-vision/wasm/${file}`,
    `${destination}/wasm/${file}`,
  );
}
let data;
try {
  data = await readFile(`${destination}/pose_landmarker_full.task`);
} catch {
  const response = await fetch(modelUrl);
  if (!response.ok)
    throw new Error(`모델 다운로드 실패: HTTP ${response.status}`);
  data = Buffer.from(await response.arrayBuffer());
}
if (createHash("sha256").update(data).digest("hex") !== expectedHash)
  throw new Error("모델 SHA-256 불일치. 파일을 사용하지 않습니다.");
await writeFile(`${destination}/pose_landmarker_full.task`, data);
const manifest = {
  sdk: "@mediapipe/tasks-vision@0.10.35",
  model: "pose_landmarker_full/float16/1",
  url: modelUrl,
  sha256: createHash("sha256").update(data).digest("hex"),
  bytes: data.length,
  license: "Apache-2.0",
};
await writeFile(
  `${destination}/manifest.json`,
  JSON.stringify(manifest, null, 2),
);
console.log(JSON.stringify(manifest, null, 2));
