import { expect, test } from "@playwright/test";
import { spawn } from "node:child_process";
import type { ChildProcess } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
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
test.afterAll(() => worker?.kill());

test("실제 3개 GLB 피팅·부위 조정·교체·코디 복원·권한 철회·캐시·터치", async ({
  page,
}, testInfo) => {
  test.setTimeout(150000);
  const api = "http://127.0.0.1:8000/api/v1",
    username = `fit_${Date.now()}_${testInfo.project.name}`,
    password = "fitting-real-test-password";
  const registered = await page.request.post(`${api}/auth/register`, {
    data: { username, password },
  });
  expect(registered.status()).toBe(201);
  const { token } = await registered.json(),
    headers = { Authorization: `Bearer ${token}` };
  const image = await readFile(
    fileURLToPath(new URL("./fixtures/garments/shirt.png", import.meta.url)),
  );
  const ids: string[] = [];
  for (const [name, kind, category, color] of [
    ["상의 하나", "티셔츠", "top", "흰색"],
    ["상의 둘", "니트", "top", "회색"],
    ["청바지", "청바지", "bottom", "파랑"],
    ["재킷", "재킷", "outer", "검정"],
    ["새 상의", "셔츠", "top", "빨강"],
  ]) {
    const created = await page.request.post(`${api}/garments`, {
      headers: {
        ...headers,
        "X-Upload-Rights": "confirmed",
        "X-Image-Storage-Consent": "confirmed",
      },
      data: {
        info: { name, garment_type: kind, category, color },
        images: {
          front: { content_type: "image/png", data: image.toString("base64") },
        },
      },
    });
    expect(created.status()).toBe(201);
    const { id } = await created.json();
    ids.push(id);
    expect(
      (
        await page.request.post(`${api}/garments/${id}/generate-3d`, {
          headers,
          data: {},
        })
      ).status(),
    ).toBe(202);
    await expect
      .poll(
        async () =>
          (
            await (
              await page.request.get(
                `${api}/garments/${id}/generation-status`,
                { headers },
              )
            ).json()
          ).generation_status,
        { timeout: 15000 },
      )
      .toBe("completed");
  }
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/#/studio");
  async function login() {
    await page.getByLabel("계정명", { exact: true }).fill(username);
    await page.getByLabel("암호", { exact: true }).fill(password);
    await page.getByRole("button", { name: "로그인", exact: true }).click();
    await page
      .getByRole("button", { name: "저장된 옷장 불러오기", exact: true })
      .click();
  }
  await login();
  const viewport = page.getByRole("region", {
    name: "개인화 3D 피팅",
    exact: true,
  });
  await expect(viewport.getByRole("status")).toContainText("피팅 3D 준비 완료");
  const canvas = viewport.locator("canvas");
  const bare = await canvas.screenshot();
  const start = Date.now();
  await page.getByLabel("상의", { exact: true }).selectOption(ids[0]);
  await expect(viewport).toHaveAttribute("data-mounted-count", "1");
  await page.getByLabel("하의", { exact: true }).selectOption(ids[2]);
  await expect(viewport).toHaveAttribute("data-mounted-count", "2");
  await page.getByLabel("겉옷", { exact: true }).selectOption(ids[3]);
  await expect(viewport).toHaveAttribute("data-mounted-count", "3");
  const coldLoadMs = Date.now() - start;
  expect((await canvas.screenshot()).equals(bare)).toBe(false);
  const bounds = JSON.parse(
    (await viewport.getAttribute("data-fitted-bounds"))!,
  );
  for (const bound of Object.values(bounds) as {
    min: number[];
    max: number[];
  }[]) {
    expect(bound.max[2] - bound.min[2]).toBeGreaterThan(0.1);
    expect(bound.min[1]).toBeGreaterThan(-0.3);
    expect(bound.max[1]).toBeLessThan(2.5);
  }
  await page.getByLabel("상의", { exact: true }).selectOption(ids[1]);
  await expect(viewport).toHaveAttribute("data-mounted-count", "3");
  await expect(page.getByLabel("하의", { exact: true })).toHaveValue(ids[2]);
  await expect(page.getByLabel("겉옷", { exact: true })).toHaveValue(ids[3]);
  await page
    .getByRole("group", { name: "피팅 슬롯", exact: true })
    .getByRole("button", { name: "겉옷", exact: true })
    .click();
  const beforeHide = await canvas.screenshot();
  await page
    .getByRole("checkbox", { name: "겉옷 숨기기", exact: true })
    .check();
  expect((await canvas.screenshot()).equals(beforeHide)).toBe(false);
  await page
    .getByRole("checkbox", { name: "겉옷 숨기기", exact: true })
    .uncheck();
  await page
    .getByRole("button", { name: "하의 선택 해제", exact: true })
    .click();
  await expect(viewport).toHaveAttribute("data-mounted-count", "2");
  await expect(page.getByLabel("상의", { exact: true })).toHaveValue(ids[1]);
  await page.getByLabel("하의", { exact: true }).selectOption(ids[2]);
  await expect(viewport).toHaveAttribute("data-mounted-count", "3");
  await page.getByText("체형 수정", { exact: true }).click();
  for (const [label, value] of [
    ["키 (cm)", "175"],
    ["어깨너비 (cm)", "42"],
    ["가슴둘레 (cm)", "106"],
    ["허리둘레 (cm)", "78"],
    ["엉덩이둘레 (cm)", "98"],
    ["팔 길이 (cm)", "56"],
    ["다리 길이 (cm)", "81"],
  ])
    await page.getByLabel(label, { exact: true }).fill(value);
  const adjusted = await canvas.screenshot();
  const threeLayerBodyResidual = Number(
    await viewport.getAttribute("data-body-penetrations"),
  );
  const threeLayerBodyBefore = Number(
    await viewport.getAttribute("data-body-before"),
  );
  const threeLayerBefore = Number(
    await viewport.getAttribute("data-layer-before"),
  );
  const threeLayerResidual = Number(
    await viewport.getAttribute("data-layer-residual"),
  );
  expect(adjusted.equals(bare)).toBe(false);
  const controls = page.getByRole("group", { name: "피팅 시점", exact: true });
  await controls.getByRole("button", { name: "측면", exact: true }).click();
  const side = await canvas.screenshot();
  expect(side.equals(adjusted)).toBe(false);
  await controls.getByRole("button", { name: "후면", exact: true }).click();
  expect((await canvas.screenshot()).equals(side)).toBe(false);
  await controls.getByRole("button", { name: "확대", exact: true }).click();
  await controls.getByRole("button", { name: "축소", exact: true }).click();
  await controls.getByRole("button", { name: "초기화", exact: true }).click();
  await canvas.scrollIntoViewIfNeeded();
  const rect = await canvas.boundingBox();
  if (!rect) throw new Error("피팅 캔버스 없음");
  const beforeDrag = await canvas.screenshot();
  await page.mouse.move(rect.x + rect.width * 0.4, rect.y + rect.height * 0.5);
  await page.mouse.down();
  await page.mouse.move(rect.x + rect.width * 0.7, rect.y + rect.height * 0.5, {
    steps: 8,
  });
  await page.mouse.up();
  expect((await canvas.screenshot()).equals(beforeDrag)).toBe(false);
  if (testInfo.project.name === "mobile") {
    const cdp = await page.context().newCDPSession(page);
    const x = rect.x + rect.width * 0.5,
      y = rect.y + rect.height * 0.5;
    const before = await canvas.screenshot();
    await cdp.send("Input.dispatchTouchEvent", {
      type: "touchStart",
      touchPoints: [
        { x: x - 25, y, id: 0 },
        { x: x + 25, y, id: 1 },
      ],
    });
    for (let step = 1; step <= 6; step++)
      await cdp.send("Input.dispatchTouchEvent", {
        type: "touchMove",
        touchPoints: [
          { x: x - 25 - step * 6, y, id: 0 },
          { x: x + 25 + step * 6, y, id: 1 },
        ],
      });
    await cdp.send("Input.dispatchTouchEvent", {
      type: "touchEnd",
      touchPoints: [],
    });
    expect((await canvas.screenshot()).equals(before)).toBe(false);
    await cdp.detach();
  }
  await page.screenshot({
    path: `test-results/phase5-${testInfo.project.name}.png`,
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const save = page.getByRole("button", {
    name: "현재 코디 저장",
    exact: true,
  });
  await expect(save).toBeDisabled();
  await page.getByRole("checkbox", { name: /같은 마네킹 복원을 위해/ }).check();
  await page.getByLabel("코디 이름", { exact: true }).fill("복원 테스트");
  const saved = page.waitForResponse(
    (r) => r.url().endsWith("/outfits") && r.request().method() === "POST",
  );
  await save.click();
  const outfit = await (await saved).json();
  expect(outfit.mannequin.values.chest).toBe(106);
  await expect(
    page.getByRole("heading", { name: "복원 테스트", exact: true }),
  ).toBeVisible();
  await page.getByLabel("가슴둘레 (cm)", { exact: true }).fill("90");
  await page
    .getByRole("button", { name: "저장된 피팅 불러오기", exact: true })
    .click();
  await expect(page.getByLabel("가슴둘레 (cm)", { exact: true })).toHaveValue(
    "106",
  );
  await page.reload();
  await login();
  await page
    .getByRole("button", { name: "복원 테스트 불러오기", exact: true })
    .click();
  await expect(viewport).toHaveAttribute("data-mounted-count", "3");
  await page.getByText("체형 수정", { exact: true }).click();
  await expect(page.getByLabel("가슴둘레 (cm)", { exact: true })).toHaveValue(
    "106",
  );
  await page
    .getByRole("combobox", { name: "3D 품질", exact: true })
    .selectOption("standard");
  await expect(canvas).toBeVisible();
  await page
    .getByRole("combobox", { name: "3D 품질", exact: true })
    .selectOption("light");
  for (let i = 0; i < 4; i++) {
    await page.getByLabel("상의", { exact: true }).selectOption(ids[i % 2]);
    await expect(viewport).toHaveAttribute("data-mounted-count", "3");
  }
  expect(
    Number(await viewport.getAttribute("data-cache-entries")),
  ).toBeLessThanOrEqual(6);
  expect(
    Number(await viewport.getAttribute("data-cache-bytes")),
  ).toBeLessThanOrEqual(8 * 1024 * 1024);
  await page.route(`**/garments/${ids[4]}/model`, (route) =>
    route.abort("failed"),
  );
  await page.getByLabel("상의", { exact: true }).selectOption(ids[4]);
  await expect(viewport).toContainText("GLB 로딩 실패");
  await page.unroute(`**/garments/${ids[4]}/model`);
  await page
    .getByRole("button", { name: "모델 다시 불러오기", exact: true })
    .click();
  await expect(viewport).toHaveAttribute("data-mounted-count", "3");
  expect(
    (
      await page.request.post(`${api}/garments/${ids[3]}/rights-withdraw`, {
        headers,
        data: {},
      })
    ).status(),
  ).toBe(204);
  await expect(viewport).toHaveAttribute("data-mounted-count", "2", {
    timeout: 7000,
  });
  await page
    .getByRole("button", { name: "코디 목록 새로고침", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "저장된 코디", exact: true }),
  ).toContainText("사용할 수 없는 의류");
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Performance.enable");
  const { metrics } = await cdp.send("Performance.getMetrics");
  await cdp.detach();
  await writeFile(
    `test-results/phase5-metrics-${testInfo.project.name}.json`,
    JSON.stringify(
      {
        coldLoadMs,
        threeLayerBodyResidual,
        threeLayerResidual,
        threeLayerBodyBefore,
        threeLayerBefore,
        cacheEntries: Number(await viewport.getAttribute("data-cache-entries")),
        cacheBytes: Number(await viewport.getAttribute("data-cache-bytes")),
        bodyResidual: Number(
          await viewport.getAttribute("data-body-penetrations"),
        ),
        layerResidual: Number(
          await viewport.getAttribute("data-layer-residual"),
        ),
        jsHeapUsedBytes: metrics.find((m) => m.name === "JSHeapUsedSize")
          ?.value,
      },
      null,
      2,
    ),
  );
  await page
    .getByRole("button", { name: "복원 테스트 코디 삭제", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "복원 테스트", exact: true }),
  ).toHaveCount(0);
  expect(errors).toEqual([]);
  expect(
    (
      await page.request.delete(`${api}/auth/account`, {
        headers,
        data: { username, password },
      })
    ).status(),
  ).toBe(204);
});
