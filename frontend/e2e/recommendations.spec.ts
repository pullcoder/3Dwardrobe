import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

test.use({ actionTimeout: 15000 });

test("실제 옷장 추천·실패 재시도·취향·이미지·피드백·저장·3D 교체·삭제", async ({
  page,
}, testInfo) => {
  test.setTimeout(150000);
  const api = "http://127.0.0.1:8000/api/v1";
  const username = `rec_${Date.now()}_${testInfo.project.name}`,
    password = "recommend-real-test-password";
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
    ["흰 티셔츠", "티셔츠", "top", "흰색"],
    ["검정 니트", "니트", "top", "검정"],
    ["청바지", "청바지", "bottom", "파랑"],
    ["회색 슬랙스", "슬랙스", "bottom", "회색"],
    ["검정 재킷", "재킷", "outer", "검정"],
  ]) {
    const response = await page.request.post(`${api}/garments`, {
      headers: {
        ...headers,
        "X-Upload-Rights": "confirmed",
        "X-Image-Storage-Consent": "confirmed",
      },
      data: {
        info: { name, garment_type: kind, category, color },
        original_image_retention: "consented_storage",
        images: {
          front: { content_type: "image/png", data: image.toString("base64") },
        },
      },
    });
    expect(response.status()).toBe(201);
    ids.push((await response.json()).id);
  }
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/#/recommend");
  await page.getByLabel("계정명", { exact: true }).fill(username);
  await page.getByLabel("암호", { exact: true }).fill(password);
  await page.getByRole("button", { name: "로그인", exact: true }).click();
  await page.getByLabel("미니멀", { exact: true }).check();
  await page.getByLabel("캐주얼", { exact: true }).check();
  await page.getByLabel("선호 핏", { exact: true }).selectOption("regular");
  await page
    .getByLabel("선호 색상 · 쉼표로 구분", { exact: true })
    .fill("흰색,검정");
  await page.getByRole("button", { name: "취향 저장", exact: true }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "취향을 비공개 저장" }),
  ).toBeVisible();
  expect(
    (
      await (
        await page.request.get(`${api}/style-preferences`, { headers })
      ).json()
    ).styles,
  ).toEqual(["minimal", "casual"]);
  await page.route(
    "**/api/v1/recommendations",
    async (route) => {
      if (route.request().method() === "POST")
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({
            error: { message: "일시적 추천 오류. 다시 시도해 주세요." },
          }),
        });
      else await route.continue();
    },
    { times: 1 },
  );
  const generate = page.getByRole("button", {
    name: "AI 코디 추천 · 규칙 기반",
    exact: true,
  });
  await generate.click();
  await expect(page.getByRole("alert")).toContainText("일시적 추천 오류");
  await generate.click();
  const cards = page.locator(".recommend-card");
  await expect(cards).toHaveCount(4);
  await expect(
    cards.first().getByRole("button", { name: "3D 입어보기", exact: true }),
  ).toBeDisabled();
  await expect
    .poll(async () => cards.first().locator("img").count())
    .toBeGreaterThan(0);
  await cards
    .first()
    .getByRole("button", { name: "추천 코디 저장", exact: true })
    .click();
  await cards
    .first()
    .getByRole("button", { name: "마음에 들어요", exact: true })
    .click();
  await expect(
    cards.first().getByRole("button", { name: "마음에 들어요", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  const saved = await (
    await page.request.get(`${api}/recommendations?saved_only=true`, {
      headers,
    })
  ).json();
  expect(saved).toHaveLength(1);
  expect(saved[0].feedback).toBe("like");
  for (const id of ids) {
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
  await generate.click();
  await expect(
    cards.first().getByRole("button", { name: "3D 입어보기", exact: true }),
  ).toBeEnabled();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 1,
  );
  expect(overflow).toBe(false);
  await page.screenshot({
    path: testInfo.outputPath("recommendations.png"),
    fullPage: true,
  });
  await cards
    .first()
    .getByRole("button", { name: "3D 입어보기", exact: true })
    .click();
  await expect(page).toHaveURL(/#\/studio$/);
  const viewport = page.getByRole("region", {
    name: "개인화 3D 피팅",
    exact: true,
  });
  await expect
    .poll(
      async () => Number(await viewport.getAttribute("data-mounted-count")),
      { timeout: 20000 },
    )
    .toBeGreaterThanOrEqual(2);
  await page.evaluate(() => {
    window.location.hash = "#/recommend";
  });
  await expect(
    cards.first().getByRole("button", { name: "3D 입어보기", exact: true }),
  ).toBeEnabled();
  await expect(page.getByLabel("미니멀", { exact: true })).toBeChecked();
  await cards
    .first()
    .getByRole("button", { name: "3D 입어보기", exact: true })
    .click();
  await page
    .getByRole("button", { name: "기존 코디 유지", exact: true })
    .click();
  await expect(page).toHaveURL(/#\/recommend$/);
  await cards
    .first()
    .getByRole("button", { name: "3D 입어보기", exact: true })
    .click();
  await page
    .getByRole("button", { name: "추천 코디로 교체", exact: true })
    .click();
  await expect(page).toHaveURL(/#\/studio$/);
  await expect
    .poll(
      async () => Number(await viewport.getAttribute("data-mounted-count")),
      { timeout: 20000 },
    )
    .toBeGreaterThanOrEqual(2);
  await page.evaluate(() => {
    window.location.hash = "#/closet";
  });
  await page.getByRole("button", { name: /코디 보관함/ }).click();
  await expect(page.locator(".recommend-card")).toHaveCount(1);
  await page
    .locator(".recommend-card")
    .getByRole("button", { name: "추천 기록 삭제", exact: true })
    .click();
  await expect(page.locator(".recommend-card")).toHaveCount(0);
  expect(
    (
      await page.request.get(`${api}/recommendations/${saved[0].id}`, {
        headers,
      })
    ).status(),
  ).toBe(404);
  expect(errors).toEqual([]);
});
