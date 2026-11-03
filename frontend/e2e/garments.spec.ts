import { expect, test } from "@playwright/test";
import { fileURLToPath } from "node:url";

test("실제 의류 AI → OCR → 수정 → 비공개 저장 → 재로그인 → 삭제", async ({
  page,
}, testInfo) => {
  test.setTimeout(240000);
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await page.goto("/#/upload");
  const username = `garment_${Date.now()}_${testInfo.project.name}`;
  const password = "stylefit-test-password";
  await page.getByLabel("계정명", { exact: true }).fill(username);
  await page.getByLabel("암호", { exact: true }).fill(password);
  await page.getByLabel("계정 작업").selectOption("register");
  await page.getByRole("button", { name: "계정 만들기", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "로그아웃", exact: true }),
  ).toBeVisible();
  await page.getByRole("checkbox", { name: /직접 촬영/ }).check();
  const fixture = (name: string) =>
    fileURLToPath(new URL(`./fixtures/garments/${name}.png`, import.meta.url));
  for (const [label, file] of [
    ["앞면 사진", "shirt"],
    ["뒷면 사진", "shirt"],
    ["사이즈표 사진", "size"],
    ["소재 및 성분표 사진", "material"],
  ]) {
    await page.getByLabel(label, { exact: true }).setInputFiles(fixture(file));
    await expect(page.getByAltText(`${label} 미리보기`)).toBeVisible();
  }
  await page
    .getByRole("checkbox", { name: /선택한 의류·라벨 사진을 로컬 서버/ })
    .check();
  // 첫 분류 요청만 네트워크 실패를 주입한다. 나머지 SAM/OCR와 재시도는 실제 서버다.
  let first = true;
  await page.route("**/garments/analyze", async (route) => {
    if (first) {
      first = false;
      await route.abort("failed");
    } else await route.continue();
  });
  await page
    .getByRole("button", { name: "AI 분석 시작 / 재시도", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "AI 분석 시작 / 재시도", exact: true }),
  ).toBeEnabled({ timeout: 150000 });
  await expect(page.getByRole("alert")).toContainText("앞면 의류 분류 중");
  await expect(page.getByAltText("front 투명 배경 결과")).toBeVisible();
  await expect(page.getByAltText("back 투명 배경 결과")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "소재표 OCR 원문", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "AI 분석 시작 / 재시도", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "AI 분석 시작 / 재시도", exact: true }),
  ).toBeEnabled({ timeout: 150000 });
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(
    page.getByRole("combobox", { name: "의류 종류", exact: true }),
  ).toHaveValue("티셔츠");
  await expect(page.getByLabel("소재 1 혼용률")).toHaveValue("65");
  await expect(page.getByLabel("치수 1 단위")).toHaveValue("cm");
  await page
    .getByRole("textbox", { name: "의류 이름 필수", exact: true })
    .fill("파란 티셔츠");
  await page.getByLabel("색상", { exact: true }).fill("사용자 확인 파랑");
  await page
    .getByRole("checkbox", { name: /분석·수정 정보와 복원 정책을/ })
    .check();
  await page.getByRole("checkbox", { name: /선택한 원본·누끼도/ }).check();
  await page
    .getByRole("button", { name: "디지털 옷장에 저장", exact: true })
    .click();
  await expect(
    page.getByRole("link", { name: /옷장에서 확인하기/ }),
  ).toBeVisible();
  await page.getByRole("link", { name: /옷장에서 확인하기/ }).click();
  await expect(
    page.getByRole("heading", { name: "파란 티셔츠", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "상세 보기 / 수정", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "의류 이름 필수", exact: true })
    .fill("수정한 파란 티셔츠");
  await page
    .getByRole("button", { name: "정보 수정 저장", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "의류 정보를 수정했습니다" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: `test-results/garments-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "로그아웃", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "수정한 파란 티셔츠", exact: true }),
  ).toHaveCount(0);
  await page.reload();
  await page.getByLabel("계정명", { exact: true }).fill(username);
  await page.getByLabel("암호", { exact: true }).fill(password);
  await page.getByRole("button", { name: "로그인", exact: true }).click();
  await page
    .getByRole("button", { name: "저장된 옷장 불러오기", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "수정한 파란 티셔츠", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "수정한 파란 티셔츠 삭제", exact: true })
    .click();
  await expect(page.getByText("첫 번째 옷을 추가해 보세요")).toBeVisible();
  await page
    .getByRole("button", { name: "계정 및 데이터 삭제", exact: true })
    .click();
  await page.getByLabel("계정 삭제 확인 암호").fill(password);
  await page
    .getByRole("button", { name: "계정 영구 삭제 확인", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "로그인", exact: true }),
  ).toBeVisible();
  expect(failures).toEqual([]);
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
});
