import { expect, test } from "@playwright/test";
import { spawn } from "node:child_process";
import type { ChildProcess } from "node:child_process";
import { fileURLToPath } from "node:url";

let worker: ChildProcess;
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
  worker = spawn(python, ["-m", "app.generation_worker"], {
    cwd: fileURLToPath(new URL("../../backend", import.meta.url)),
    stdio: "ignore",
    windowsHide: true,
  });
});
test.afterAll(() => {
  worker?.kill();
});

test("실제 워커의 상의·바지·겉옷 GLB → 재조회 → 360도 뷰어 → 삭제", async ({
  page,
}, testInfo) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/#/upload");
  const username = `mesh_${Date.now()}_${testInfo.project.name}`;
  const password = "mesh-real-test-password";
  await page.getByLabel("계정명", { exact: true }).fill(username);
  await page.getByLabel("암호", { exact: true }).fill(password);
  await page.getByLabel("계정 작업").selectOption("register");
  const registered = page.waitForResponse("**/auth/register");
  await page.getByRole("button", { name: "계정 만들기", exact: true }).click();
  const { token } = await (await registered).json();
  const headers = { Authorization: `Bearer ${token}` };
  const photo = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 100;
    canvas.height = 150;
    canvas.getContext("2d")!.fillRect(20, 20, 60, 100);
    return canvas.toDataURL("image/png").split(",")[1];
  });
  const canvasImages: string[] = [];
  for (const [kind, category] of [
    ["티셔츠", "top"],
    ["청바지", "bottom"],
    ["재킷", "outer"],
  ]) {
    await page.goto("/#/upload");
    await page.getByRole("checkbox", { name: /직접 촬영/ }).check();
    await page.getByLabel("앞면 사진", { exact: true }).setInputFiles({
      name: "test-shirt.png",
      mimeType: "image/png",
      buffer: Buffer.from(photo, "base64"),
    });
    await page
      .getByRole("textbox", { name: "의류 이름 필수", exact: true })
      .fill(`3D ${kind}`);
    await page
      .getByRole("combobox", { name: "분류", exact: true })
      .selectOption(category);
    await page
      .getByRole("combobox", { name: "의류 종류", exact: true })
      .selectOption(kind);
    await page.getByLabel("색상", { exact: true }).fill("파랑");
    await page
      .getByRole("checkbox", { name: /분석·수정 정보와 복원 정책을/ })
      .check();
    const saved = page.waitForResponse(
      (r) => r.url().endsWith("/garments") && r.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "디지털 옷장에 저장", exact: true })
      .click();
    const garment = await (await saved).json();
    await page.getByRole("link", { name: /옷장에서 확인하기/ }).click();
    const card = page.locator("article").filter({
      has: page.getByRole("heading", { name: `3D ${kind}`, exact: true }),
    });
    await card.getByRole("button", { name: "3D 복원", exact: true }).click();
    const panel = page.getByRole("region", {
      name: "의류 3D 복원",
      exact: true,
    });
    await expect(
      panel.getByText("자동 선택 모드: A", { exact: true }),
    ).toBeVisible();
    const queued = page.waitForResponse("**/generate-3d");
    await panel
      .getByRole("button", { name: "3D 모델 생성", exact: true })
      .click();
    expect((await queued).status()).toBe(202);
    await expect(
      panel.getByText("3D 의류 준비 완료", { exact: true }),
    ).toBeVisible({ timeout: 20000 });
    const model = await page.request.get(
      `http://127.0.0.1:8000/api/v1/garments/${garment.id}/model`,
      { headers },
    );
    expect(model.status()).toBe(200);
    expect((await model.body()).subarray(0, 4).toString()).toBe("glTF");
    const canvas = panel.locator("canvas");
    await expect(canvas).toBeVisible();
    const front = await canvas.screenshot();
    canvasImages.push(front.toString("base64"));
    const controls = panel.getByRole("group", { name: "의류 시점" });
    await controls.getByRole("button", { name: "측면", exact: true }).click();
    const side = await canvas.screenshot();
    expect(side.equals(front)).toBe(false);
    await controls.getByRole("button", { name: "후면", exact: true }).click();
    const back = await canvas.screenshot();
    expect(back.equals(side)).toBe(false);
    await controls.getByRole("button", { name: "확대", exact: true }).click();
    expect((await canvas.screenshot()).equals(back)).toBe(false);
    await controls.getByRole("button", { name: "축소", exact: true }).click();
    await controls.getByRole("button", { name: "초기화", exact: true }).click();
    const bounds = await canvas.boundingBox();
    if (!bounds) throw new Error("3D canvas가 없습니다.");
    const beforeDrag = await canvas.screenshot();
    await page.mouse.move(
      bounds.x + bounds.width * 0.4,
      bounds.y + bounds.height * 0.5,
    );
    await page.mouse.down();
    await page.mouse.move(
      bounds.x + bounds.width * 0.8,
      bounds.y + bounds.height * 0.5,
      { steps: 10 },
    );
    await page.mouse.up();
    expect((await canvas.screenshot()).equals(beforeDrag)).toBe(false);
    if (testInfo.project.name === "mobile") {
      await canvas.scrollIntoViewIfNeeded();
      const touchBounds = await canvas.boundingBox();
      if (!touchBounds) throw new Error("터치 대상 canvas가 없습니다.");
      const touch = await page.context().newCDPSession(page);
      const x = touchBounds.x + touchBounds.width * 0.5;
      const y = touchBounds.y + touchBounds.height * 0.5;
      const beforeTouch = await canvas.screenshot();
      await touch.send("Input.dispatchTouchEvent", {
        type: "touchStart",
        touchPoints: [{ x, y, id: 0 }],
      });
      for (let step = 1; step <= 6; step++) {
        await touch.send("Input.dispatchTouchEvent", {
          type: "touchMove",
          touchPoints: [{ x: x + step * 12, y, id: 0 }],
        });
      }
      await touch.send("Input.dispatchTouchEvent", {
        type: "touchEnd",
        touchPoints: [],
      });
      expect((await canvas.screenshot()).equals(beforeTouch)).toBe(false);
      const beforePinch = await canvas.screenshot();
      await touch.send("Input.dispatchTouchEvent", {
        type: "touchStart",
        touchPoints: [
          { x: x - 25, y, id: 0 },
          { x: x + 25, y, id: 1 },
        ],
      });
      for (let step = 1; step <= 6; step++) {
        await touch.send("Input.dispatchTouchEvent", {
          type: "touchMove",
          touchPoints: [
            { x: x - 25 - step * 5, y, id: 0 },
            { x: x + 25 + step * 5, y, id: 1 },
          ],
        });
      }
      await touch.send("Input.dispatchTouchEvent", {
        type: "touchEnd",
        touchPoints: [],
      });
      expect((await canvas.screenshot()).equals(beforePinch)).toBe(false);
      await touch.detach();
    }
    await page.screenshot({
      path: `test-results/phase4-${category}-${testInfo.project.name}.png`,
      fullPage: true,
    });
    const overflow = await page.evaluate(() =>
      [...document.querySelectorAll("input, canvas, section")]
        .filter((e) => e.getBoundingClientRect().right > innerWidth + 1)
        .map((e) => ({
          html: e.outerHTML.slice(0, 220),
          width: e.getBoundingClientRect().width,
          parent: e.parentElement?.className,
        })),
    );
    expect(overflow).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await panel
      .getByRole("button", { name: "3D 모델 삭제·작업 취소", exact: true })
      .click();
    await expect(canvas).toHaveCount(0);
    expect(
      (
        await page.request.get(
          `http://127.0.0.1:8000/api/v1/garments/${garment.id}/model`,
          { headers },
        )
      ).status(),
    ).toBe(404);
    expect(
      (
        await page.request.delete(
          `http://127.0.0.1:8000/api/v1/garments/${garment.id}`,
          { headers },
        )
      ).status(),
    ).toBe(204);
  }
  expect(new Set(canvasImages).size).toBe(3);
  expect(errors).toEqual([]);
  expect(
    (
      await page.request.delete("http://127.0.0.1:8000/api/v1/auth/account", {
        headers,
        data: { username, password },
      })
    ).status(),
  ).toBe(204);
});
