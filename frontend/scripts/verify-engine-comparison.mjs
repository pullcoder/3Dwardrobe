// 합성 비교 산출물의 실제 Three.js GLB 재로딩. AI 결과를 대신 만들지 않는다.
import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { Box3, Mesh, Vector3 } from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

const directory = new URL(
  "../../backend/storage/engine-comparison/",
  import.meta.url,
);
const results = [];
for (const file of ["tshirt-template.glb", "wide-pants-template.glb"]) {
  const bytes = await readFile(new URL(file, directory));
  const { scene } = await new GLTFLoader().parseAsync(
    bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    "",
  );
  const size = new Box3().setFromObject(scene).getSize(new Vector3());
  assert(size.x > 0.1 && size.y > 0.1 && size.z > 0.01);
  let triangles = 0;
  scene.traverse((object) => {
    if (!(object instanceof Mesh)) return;
    triangles += object.geometry.index.count / 3;
    object.geometry.dispose();
    for (const material of Array.isArray(object.material)
      ? object.material
      : [object.material])
      material.dispose();
  });
  assert(triangles > 100);
  results.push({
    file,
    reloaded: true,
    triangles,
    size_m: size.toArray(),
    engine: "template",
    ai_executed: false,
  });
}
await writeFile(
  new URL("three-reload.json", directory),
  JSON.stringify(results, null, 2),
);
console.log(JSON.stringify(results, null, 2));
