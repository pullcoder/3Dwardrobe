import { expect, test } from "@playwright/test";

test("6종 입체 의류·3겹 착용·부위 변형·교체·제거·360도", async ({
  page,
}, testInfo) => {
  test.setTimeout(150000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/#/studio");
  await page
    .getByRole("button", { name: "템플릿 만들기", exact: true })
    .click();
  const editor = page.getByRole("region", {
    name: "6종 입체 의류 템플릿 편집기",
  });
  const viewport = editor.getByRole("region", {
    name: "의류 템플릿 착용 결과",
  });
  await expect(viewport.getByRole("status")).toContainText(
    "템플릿 3D 준비 완료",
  );
  await expect(viewport).toHaveAttribute("data-mounted-count", "2");
  const canvas = viewport.locator("canvas");
  await expect(canvas).toBeVisible();
  const signatures = new Set<string>();
  for (const [category, templates] of [
    ["top", ["short_tshirt", "long_tshirt"]],
    ["pants", ["jeans", "slacks"]],
    ["outer", ["zip_hoodie", "jacket"]],
  ] as const) {
    await editor
      .getByLabel("의류 종류", { exact: true })
      .selectOption(category);
    for (const template of templates) {
      await editor
        .getByLabel("의류 템플릿", { exact: true })
        .selectOption(template);
      await expect(viewport).toHaveAttribute(
        "data-templates",
        new RegExp(template),
      );
      const signature = (await viewport.getAttribute("data-shape-signature"))!;
      signatures.add(`${template}:${signature}`);
      await canvas.screenshot({ path: testInfo.outputPath(`${template}.png`) });
      const controls = editor.getByRole("slider");
      for (let i = 0; i < (await controls.count()); i++) {
        const before = (await viewport.getAttribute("data-shape-signature"))!;
        await controls.nth(i).focus();
        await controls.nth(i).press("End");
        await expect(viewport).not.toHaveAttribute(
          "data-shape-signature",
          before,
        );
      }
      await editor
        .getByRole("button", { name: "형태 초기화", exact: true })
        .click();
      await expect(viewport).toHaveAttribute("data-shape-signature", signature);
    }
  }
  expect(signatures.size).toBe(6);
  await expect(viewport).toHaveAttribute("data-mounted-count", "3");
  expect(Number(await viewport.getAttribute("data-triangles"))).toBeLessThan(
    36000,
  );
  await editor.getByLabel("부위별 색상으로 보기").check();
  await canvas.screenshot({ path: testInfo.outputPath("semantic-parts.png") });
  const views = viewport.getByRole("group", { name: "템플릿 시점" });
  const front = await canvas.screenshot();
  await views.getByRole("button", { name: "측면", exact: true }).click();
  const side = await canvas.screenshot({
    path: testInfo.outputPath("side.png"),
  });
  expect(side.equals(front)).toBe(false);
  await views.getByRole("button", { name: "후면", exact: true }).click();
  expect((await canvas.screenshot()).equals(side)).toBe(false);
  await views.getByRole("button", { name: "시점 초기화", exact: true }).click();
  const box = await canvas.boundingBox();
  if (!box) throw new Error("입체 의류 캔버스를 찾지 못했습니다.");
  const beforeDrag = await canvas.screenshot();
  await page.mouse.move(box.x + box.width * 0.4, box.y + box.height * 0.4);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.7, box.y + box.height * 0.55, {
    steps: 8,
  });
  await page.mouse.up();
  expect((await canvas.screenshot()).equals(beforeDrag)).toBe(false);
  await editor
    .getByRole("button", { name: "선택 의류 제거", exact: true })
    .click();
  await expect(viewport).toHaveAttribute("data-mounted-count", "2");
  await editor
    .getByRole("button", { name: "의류 모두 제거", exact: true })
    .click();
  await expect(viewport).toHaveAttribute("data-mounted-count", "0");
  await expect(canvas).toBeVisible();
  await editor
    .getByRole("button", { name: "전체 의류 초기화", exact: true })
    .click();
  await expect(viewport).toHaveAttribute("data-mounted-count", "2");
  await editor
    .getByLabel("렌더링 품질", { exact: true })
    .selectOption("standard");
  await expect(canvas).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("button", { name: "내 옷장 입어보기", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "개인화 3D 피팅" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
