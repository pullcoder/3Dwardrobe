// 서버의 자체 검증과 독립적으로 실제 Three.js 로더로 GLB를 다시 읽는다.
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";
import { Box3, Mesh, Vector3 } from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

const directory = new URL(
  "../../backend/storage/phase4-validation/",
  import.meta.url,
);
const results = [];
for (const name of ["tshirt", "pants", "jacket"]) {
  const bytes = await readFile(new URL(`${name}.glb`, directory));
  const buffer = bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength,
  );
  const { scene } = await new GLTFLoader().parseAsync(buffer, "");
  const size = new Box3().setFromObject(scene).getSize(new Vector3());
  assert(size.x > 0.1 && size.y > 0.1 && size.z > 0.05);
  let meshCount = 0,
    triangles = 0;
  scene.traverse((object) => {
    if (!(object instanceof Mesh)) return;
    meshCount++;
    const position = object.geometry.getAttribute("position");
    const normal = object.geometry.getAttribute("normal");
    const indices = object.geometry.index;
    assert(
      indices && position.count === normal.count && indices.count % 3 === 0,
    );
    assert(object.material && !object.material.map);
    const a = new Vector3(),
      b = new Vector3(),
      c = new Vector3(),
      cross = new Vector3();
    for (let i = 0; i < indices.count; i += 3) {
      a.fromBufferAttribute(position, indices.getX(i));
      b.fromBufferAttribute(position, indices.getX(i + 1));
      c.fromBufferAttribute(position, indices.getX(i + 2));
      cross.crossVectors(b.sub(a), c.sub(a));
      assert(cross.lengthSq() > 1e-16, "퇴화 삼각형");
    }
    for (let i = 0; i < normal.count; i++) {
      a.fromBufferAttribute(normal, i);
      assert(Math.abs(a.length() - 1) < 1e-5, "잘못된 법선");
    }
    triangles += indices.count / 3;
    object.geometry.dispose();
    object.material.dispose();
  });
  assert(meshCount > 1 && triangles > 100);
  const root = scene.getObjectByName("garment_root");
  assert.equal(root.userData.unit, "meter");
  assert.equal(root.userData.coordinate_system, "y_up_z_front");
  results.push({
    file: `${name}.glb`,
    bytes: bytes.length,
    meshCount,
    triangles,
    sizeMeters: size.toArray(),
    reloaded: true,
  });
}
await writeFile(
  fileURLToPath(new URL("three-validation.json", directory)),
  JSON.stringify(results, null, 2),
);
console.log(JSON.stringify(results, null, 2));
