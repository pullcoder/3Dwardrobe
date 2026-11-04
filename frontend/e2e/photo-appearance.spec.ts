import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

test.beforeAll(() => {
  const python =
    process.env.STYLEFIT_TEST_PYTHON ||
    fileURLToPath(
      new URL(
        process.platform === "win32"
          ? "../../backend/.venv/Scripts/python.exe"
          : "../../backend/.venv/bin/python",
        import.meta.url,
      ),
    );
  execFileSync(python, [
    fileURLToPath(
      new URL(
        "../../backend/scripts/verify_photo_appearance.py",
        import.meta.url,
      ),
    ),
  ]);
});

for (const name of ["tshirt", "pants"]) {
  test(`${name}: 실제 사진 아틀라스 GLB의 앞뒤 구분·상하 방향·렌더링`, async ({
    page,
  }, testInfo) => {
    const glb = await readFile(
      new URL(
        `../../backend/storage/photo-appearance/${name}.glb`,
        import.meta.url,
      ),
    );
    await page.goto("/");
    await page.setContent(
      '<main><h1>합성 색상 표식 · 사진 투영 검증</h1><button id="front">앞면</button><button id="back">뒷면</button><div id="render"></div></main>',
    );
    await page.evaluate(async (encoded) => {
      const threePath = "/node_modules/.vite/deps/three.js";
      const loaderPath =
        "/node_modules/three/examples/jsm/loaders/GLTFLoader.js";
      const THREE = await import(threePath);
      const { GLTFLoader } = await import(loaderPath);
      const binary = Uint8Array.from(atob(encoded), (c) => c.charCodeAt(0));
      const { scene: garment } = await new GLTFLoader().parseAsync(
        binary.buffer,
        "",
      );
      const scene = new THREE.Scene();
      scene.background = new THREE.Color("#eceff2");
      scene.add(garment);
      scene.add(new THREE.AmbientLight(0xffffff, 2));
      const renderer = new THREE.WebGLRenderer({
        antialias: true,
        preserveDrawingBuffer: true,
      });
      renderer.setSize(340, 500);
      const container = document.getElementById("render")!;
      container.appendChild(renderer.domElement);
      const bounds = new THREE.Box3().setFromObject(garment);
      const center = bounds.getCenter(new THREE.Vector3());
      const size = bounds.getSize(new THREE.Vector3());
      const camera = new THREE.PerspectiveCamera(38, 340 / 500, 0.01, 20);
      const draw = (back: boolean) => {
        camera.position.set(
          0,
          center.y,
          (back ? -1 : 1) * Math.max(size.y, size.x / (340 / 500)) * 1.8,
        );
        camera.lookAt(center);
        renderer.render(scene, camera);
        renderer.domElement.dataset.view = back ? "back" : "front";
      };
      document.getElementById("front")!.onclick = () => draw(false);
      document.getElementById("back")!.onclick = () => draw(true);
      draw(false);
    }, glb.toString("base64"));
    const canvas = page.locator("canvas");
    await expect(canvas).toHaveAttribute("data-view", "front");
    const front = await canvas.screenshot({
      path: testInfo.outputPath(`${name}-front.png`),
    });
    // 실제 픽셀 상단 빨강/하단 파랑: UV 상하 반전 회귀를 화면에서도 확인한다.
    const sample = () =>
      page.evaluate(() => {
        const canvas = document.querySelector("canvas")!;
        const copy = document.createElement("canvas");
        copy.width = canvas.width;
        copy.height = canvas.height;
        const ctx = copy.getContext("2d")!;
        ctx.drawImage(canvas, 0, 0);
        const pixel = (y: number) => [
          ...ctx.getImageData(
            Math.floor(copy.width / 2) + 15,
            Math.floor(copy.height * y),
            1,
            1,
          ).data,
        ];
        return { upper: pixel(0.4), lower: pixel(0.6) };
      });
    const before = await sample();
    expect(before.upper[0]).toBeGreaterThan(before.upper[2] + 80);
    expect(before.lower[2]).toBeGreaterThan(before.lower[0] + 80);
    await page.getByRole("button", { name: "뒷면", exact: true }).click();
    await expect(canvas).toHaveAttribute("data-view", "back");
    const back = await canvas.screenshot({
      path: testInfo.outputPath(`${name}-back.png`),
    });
    expect(back.equals(front)).toBe(false);
    const after = await sample();
    expect(after.upper[0]).toBeGreaterThan(after.upper[2] + 80);
    expect(after.upper[1]).toBeGreaterThan(after.upper[2] + 80);
  });
}
