import { expect, test } from "@playwright/test";
import { readFile, writeFile } from "node:fs/promises";

test("연결 패널 티셔츠·사진 폭·목과 소매 개구부·세 시점·하의 레이어", async ({
  page,
}, testInfo) => {
  test.setTimeout(150000);
  const api = "http://127.0.0.1:8000/api/v1";
  const username = `pants_${Date.now()}_${testInfo.project.name}`,
    password = "pants-silhouette-real-test";
  const registered = await page.request.post(`${api}/auth/register`, {
    data: { username, password },
  });
  expect(registered.status()).toBe(201);
  const { token } = await registered.json(),
    headers = { Authorization: `Bearer ${token}` };
  const reference = process.env.STYLEFIT_TEE_REFERENCE;
  const photo = reference
    ? await readFile(reference)
    : Buffer.from(
        await page.evaluate(() => {
          const canvas = document.createElement("canvas");
          canvas.width = 900;
          canvas.height = 700;
          const ctx = canvas.getContext("2d")!;
          ctx.fillStyle = "#ecebe6";
          ctx.beginPath();
          const points = [
            [210, 660],
            [205, 300],
            [80, 340],
            [20, 180],
            [225, 65],
            [355, 35],
            [380, 65],
            [450, 85],
            [520, 65],
            [545, 35],
            [675, 65],
            [880, 180],
            [820, 340],
            [695, 300],
            [690, 660],
          ];
          points.forEach(([x, y], index) =>
            index ? ctx.lineTo(x, y) : ctx.moveTo(x, y),
          );
          ctx.closePath();
          ctx.fill();
          return canvas.toDataURL("image/png").split(",")[1];
        }),
        "base64",
      );
  await writeFile(testInfo.outputPath("reference-tee.png"), photo);
  const source = { content_type: "image/png", data: photo.toString("base64") };
  const created = await page.request.post(`${api}/garments`, {
    headers: {
      ...headers,
      "X-Upload-Rights": "confirmed",
      "X-Image-Storage-Consent": "confirmed",
    },
    data: {
      info: {
        name: "연결 패널 티셔츠",
        garment_type: "티셔츠",
        category: "top",
        color: "흰색",
        pattern: "무지",
        fit: "unknown",
      },
      images: { front: source, cutout_front: source },
      original_image_retention: "consented_storage",
    },
  });
  expect(created.status()).toBe(201);
  const item = await created.json();
  expect(item.analysis.silhouette.method).toBe("alpha_mask");
  await page.goto("/#/closet");
  await page.getByLabel("계정명", { exact: true }).fill(username);
  await page.getByLabel("암호", { exact: true }).fill(password);
  await page.getByRole("button", { name: "로그인", exact: true }).click();
  await page
    .getByRole("button", { name: "저장된 옷장 불러오기", exact: true })
    .click();
  const card = page.locator("article").filter({
    has: page.getByRole("heading", { name: "연결 패널 티셔츠", exact: true }),
  });
  await card.getByRole("button", { name: "3D 복원", exact: true }).click();
  const panel = page.getByRole("region", { name: "의류 3D 복원", exact: true });
  const beforePath = process.env.STYLEFIT_TEE_BEFORE_MODEL;
  if (beforePath) {
    const oldModel = await readFile(beforePath);
    await page.route(`**/garments/${item.id}/model`, (route) =>
      route.fulfill({
        status: 200,
        contentType: "model/gltf-binary",
        body: oldModel,
      }),
    );
  }
  await panel
    .getByRole("button", { name: "3D 모델 생성", exact: true })
    .click();
  await expect(
    panel.getByText("3D 의류 준비 완료", { exact: true }),
  ).toBeVisible({ timeout: 20000 });
  const canvas = panel.locator("canvas"),
    controls = panel.getByRole("group", { name: "의류 시점" });
  if (beforePath) {
    for (const [view, label] of [
      ["front", "정면"],
      ["side", "측면"],
      ["back", "후면"],
    ]) {
      await controls.getByRole("button", { name: label, exact: true }).click();
      await canvas.screenshot({
        path: testInfo.outputPath(`before-${view}.png`),
      });
    }
    await page.unroute(`**/garments/${item.id}/model`);
    const regeneration = page.waitForResponse(
      (response) =>
        response.url().endsWith("/generate-3d") &&
        response.request().method() === "POST",
    );
    await panel
      .getByRole("button", { name: "3D 모델 재생성", exact: true })
      .click();
    const expectedJob = (await (await regeneration).json()).job_id;
    await expect
      .poll(
        async () =>
          await (
            await page.request.get(
              `${api}/garments/${item.id}/generation-status`,
              { headers },
            )
          ).json(),
        { timeout: 20000 },
      )
      .toMatchObject({
        job_id: expectedJob,
        generation_status: "completed",
        model_ready: true,
      });
    await expect(
      panel.getByText("3D 의류 준비 완료", { exact: true }),
    ).toBeVisible({ timeout: 20000 });
  }
  const modelResponse = await page.request.get(
    `${api}/garments/${item.id}/model`,
    { headers },
  );
  expect(modelResponse.status()).toBe(200);
  const binary = await modelResponse.body();
  await writeFile(testInfo.outputPath("tee-after-A.glb"), binary);
  const document = JSON.parse(
    binary.subarray(20, 20 + binary.readUInt32LE(12)).toString(),
  );
  const metadata = document.nodes[0].extras;
  expect(metadata.fitting_contract).toBe("stylefit.panel.v3");
  expect(metadata.shape_source).toBe("photo_silhouette_estimate");
  expect(metadata.texture_policy).toBe("solid_color");
  expect(metadata.triangle_count).toBeGreaterThan(1000);
  expect(metadata.mesh_quality).toMatchObject({
    connected_components: 1,
    boundary_loops: 4,
    inconsistent_winding_edges: 0,
  });
  await writeFile(
    testInfo.outputPath("tee-metadata.json"),
    JSON.stringify(metadata, null, 2),
  );
  const pictures: Buffer[] = [];
  for (const [view, label] of [
    ["front", "정면"],
    ["side", "측면"],
    ["back", "후면"],
  ]) {
    await controls.getByRole("button", { name: label, exact: true }).click();
    pictures.push(
      await canvas.screenshot({
        path: testInfo.outputPath(`after-${view}.png`),
      }),
    );
  }
  expect(pictures[0].equals(pictures[1])).toBe(false);
  expect(pictures[1].equals(pictures[2])).toBe(false);
  const pantsPhoto = Buffer.from(
    await page.evaluate(() => {
      const canvas = document.createElement("canvas");
      canvas.width = 400;
      canvas.height = 700;
      const ctx = canvas.getContext("2d")!;
      ctx.fillStyle = "#707079";
      ctx.beginPath();
      [
        [90, 20],
        [310, 20],
        [335, 220],
        [360, 670],
        [215, 670],
        [200, 335],
        [185, 670],
        [40, 670],
        [65, 220],
      ].forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.closePath();
      ctx.fill();
      return canvas.toDataURL("image/png").split(",")[1];
    }),
    "base64",
  );
  const pantsSource = {
    content_type: "image/png",
    data: pantsPhoto.toString("base64"),
  };
  const pants = await (
    await page.request.post(`${api}/garments`, {
      headers: {
        ...headers,
        "X-Upload-Rights": "confirmed",
        "X-Image-Storage-Consent": "confirmed",
      },
      data: {
        info: {
          name: "레이어 검증 팬츠",
          garment_type: "슬랙스",
          category: "bottom",
          color: "회색",
          fit: "와이드핏",
        },
        images: { front: pantsSource, cutout_front: pantsSource },
        original_image_retention: "consented_storage",
      },
    })
  ).json();
  expect(
    (
      await page.request.post(`${api}/garments/${pants.id}/generate-3d`, {
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
              `${api}/garments/${pants.id}/generation-status`,
              { headers },
            )
          ).json()
        ).model_ready,
      { timeout: 30000 },
    )
    .toBe(true);
  await page.getByRole("button", { name: "상세 닫기", exact: true }).click();
  await page
    .getByRole("button", { name: "저장된 옷장 불러오기", exact: true })
    .click();
  await page.evaluate(() => {
    window.location.hash = "#/studio";
  });
  await page.getByLabel("상의", { exact: true }).selectOption(item.id);
  const viewport = page.getByRole("region", {
    name: "개인화 3D 피팅",
    exact: true,
  });
  await expect(viewport).toHaveAttribute("data-mounted-count", "1", {
    timeout: 20000,
  });
  await page.getByLabel("하의", { exact: true }).selectOption(pants.id);
  await expect(viewport).toHaveAttribute("data-mounted-count", "2", {
    timeout: 20000,
  });
  const bounds = JSON.parse(
    (await viewport.getAttribute("data-fitted-bounds"))!,
  );
  expect(bounds.top.max[0] - bounds.top.min[0]).toBeGreaterThan(0.4);
  for (const [view, label] of [
    ["front", "정면"],
    ["side", "측면"],
    ["back", "후면"],
  ]) {
    await viewport.getByRole("button", { name: label, exact: true }).click();
    await viewport
      .locator("canvas")
      .screenshot({ path: testInfo.outputPath(`fitted-${view}.png`) });
  }
  await writeFile(
    testInfo.outputPath("fit-report.json"),
    JSON.stringify({
      body_remaining: await viewport.getAttribute("data-body-penetrations"),
      layer_before: await viewport.getAttribute("data-layer-before"),
      layer_remaining: await viewport.getAttribute("data-layer-residual"),
    }),
  );
  expect(
    Number(await viewport.getAttribute("data-layer-residual")),
  ).toBeLessThanOrEqual(
    Number(await viewport.getAttribute("data-layer-before")),
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 1,
    ),
  ).toBe(false);
});
