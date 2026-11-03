import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

async function navigate(page: Page, name: string) {
  const menu = page.getByRole("button", { name: "메뉴 열기", exact: true });
  const mobile = await page.evaluate(
    () => matchMedia("(max-width: 820px)").matches,
  );
  if (mobile) {
    // 이전 해시 이동의 메뉴 닫힘이 반영되기 전에 다음 클릭을 시도하지 않는다.
    await expect(menu).toBeVisible();
    await menu.click();
  }
  await page
    .getByRole("navigation", { name: "주 메뉴" })
    .getByRole("link", { name, exact: true })
    .click();
  if (mobile) await expect(menu).toBeVisible();
}

async function makePhoto(page: Page) {
  const data = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 120;
    canvas.height = 160;
    const context = canvas.getContext("2d")!;
    context.fillStyle = "#c4b4d9";
    context.fillRect(0, 0, 120, 160);
    context.fillStyle = "#fff";
    context.fillRect(30, 30, 60, 95);
    return canvas.toDataURL("image/png").split(",")[1];
  });
  return {
    name: "my-shirt.png",
    mimeType: "image/png",
    buffer: Buffer.from(data, "base64"),
  };
}

test("8개 화면을 이동하고 미연결 기능을 확인한다", async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "오늘의 스타일, 나답게.",
  );
  await page.screenshot({
    path: `test-results/dashboard-${testInfo.project.name}.png`,
    fullPage: true,
  });
  const screens = [
    ["내 체형 분석", "내 몸을 이해하는 첫걸음"],
    ["3D 마네킹", "3D 마네킹 편집"],
    ["의류 등록", "내 옷의 새로운 시작"],
    ["피팅 스튜디오", "3D 피팅 스튜디오"],
    ["AI 코디 추천", "AI 코디 추천"],
    ["디지털 옷장", "나의 디지털 옷장"],
    ["설정 및 개인정보", "설정 및 개인정보 관리"],
  ];
  for (const [name, heading] of screens) {
    await navigate(page, name);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
  await page
    .getByRole("button", { name: "API 연결 확인", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "로컬 API 연결됨" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("사진 선택 → 실제 API 검증 → 초안 → 필터 → 슬롯 → 삭제", async ({
  page,
}, testInfo) => {
  let validations = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/uploads/validate")) validations++;
  });
  await page.goto("/#/upload");
  await expect(
    page.getByRole("button", { name: "세션 초안에 추가" }),
  ).toBeDisabled();
  await page.getByRole("checkbox", { name: /직접 촬영/ }).check();
  await page
    .getByLabel("앞면 사진", { exact: true })
    .setInputFiles(await makePhoto(page));
  await expect(page.getByAltText("앞면 사진 미리보기")).toBeVisible();
  expect(validations).toBe(0);
  await page.getByRole("textbox", { name: /의류 이름/ }).fill("내 라벤더 셔츠");
  await page.getByRole("checkbox", { name: /선택한 앞면 사진을 로컬/ }).check();
  await page
    .getByRole("button", { name: "앞면 사진 형식 검증", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("120 × 160px");
  expect(validations).toBe(1);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `test-results/upload-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "세션 초안에 추가" }).click();
  await page.getByRole("link", { name: /옷장에서 확인하기/ }).click();
  await expect(
    page.getByRole("heading", { name: "내 라벤더 셔츠" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "하의", exact: true }).click();
  await expect(page.getByText("조건에 맞는 옷이 없어요")).toBeVisible();
  await page.getByRole("button", { name: "상의", exact: true }).click();
  await page.getByRole("textbox", { name: "의류 이름 검색" }).fill("다른 옷");
  await expect(page.getByText("조건에 맞는 옷이 없어요")).toBeVisible();
  await page.getByRole("textbox", { name: "의류 이름 검색" }).fill("");
  await navigate(page, "피팅 스튜디오");
  await page
    .getByRole("combobox", { name: "상의", exact: true })
    .selectOption({ label: "내 라벤더 셔츠 (3D 미준비)" });
  await expect(
    page.getByRole("button", { name: "상의 선택 해제" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "현재 코디 저장", exact: true }),
  ).toBeDisabled();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `test-results/studio-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await navigate(page, "디지털 옷장");
  await page.getByRole("button", { name: "내 라벤더 셔츠 삭제" }).click();
  await expect(page.getByText("첫 번째 옷을 추가해 보세요")).toBeVisible();
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
});

test("잘못된 파일·사진 제거·전송 실패를 명확히 표시한다", async ({ page }) => {
  await page.goto("/#/upload");
  await page.getByRole("checkbox", { name: /직접 촬영/ }).check();
  await page.getByLabel("앞면 사진", { exact: true }).setInputFiles({
    name: "broken.png",
    mimeType: "image/png",
    buffer: Buffer.from("broken"),
  });
  await expect(page.getByRole("alert")).toContainText(
    "사진을 읽을 수 없습니다",
  );
  await page
    .getByLabel("앞면 사진", { exact: true })
    .setInputFiles(await makePhoto(page));
  await page.getByRole("button", { name: "앞면 사진 제거" }).click();
  await expect(page.getByAltText("앞면 사진 미리보기")).toHaveCount(0);
  await page
    .getByLabel("앞면 사진", { exact: true })
    .setInputFiles(await makePhoto(page));
  await page.getByRole("checkbox", { name: /선택한 앞면 사진을 로컬/ }).check();
  await page.route("**/uploads/validate", (route) => route.abort("failed"));
  await page
    .getByRole("button", { name: "앞면 사진 형식 검증", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "로컬 API에 연결할 수 없습니다",
  );
});

test("치수는 탭 메모리에서만 유지하고 전체 초기화·새로고침으로 제거한다", async ({
  page,
}) => {
  await page.goto("/#/body");
  await page.getByRole("spinbutton", { name: /^키/ }).fill("172");
  await page.getByRole("button", { name: "입력값 확인", exact: true }).click();
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "서버에는 저장하지 않았습니다" }),
  ).toBeVisible();
  await navigate(page, "3D 마네킹");
  await expect(page.getByRole("spinbutton", { name: /^키/ })).toHaveValue(
    "172",
  );
  await navigate(page, "설정 및 개인정보");
  await page
    .getByRole("button", { name: "세션 데이터 초기화", exact: true })
    .click();
  await page.getByRole("button", { name: "모두 초기화", exact: true }).click();
  await navigate(page, "내 체형 분석");
  await expect(page.getByRole("spinbutton", { name: /^키/ })).toHaveValue("");
  await page.getByRole("spinbutton", { name: /^키/ }).fill("180");
  await page.reload();
  await expect(page.getByRole("spinbutton", { name: /^키/ })).toHaveValue("");
});
