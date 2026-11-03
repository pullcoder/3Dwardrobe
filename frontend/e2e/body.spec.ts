import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { readFile } from "node:fs/promises";

async function photoMode(page: Page) {
  await page.goto("/#/body");
  await page
    .getByRole("button", { name: "사진 분석 체형", exact: true })
    .click();
  await page.getByRole("spinbutton", { name: /^키/ }).fill("175");
  await page
    .getByRole("checkbox", { name: /본인 사진이며 기기 내 분석/ })
    .check();
}

test("실제 전신 사진의 33개 관절, 추정값 재계산, 두 체형 분리, 사진 폐기", async ({
  page,
  context,
}, testInfo) => {
  test.setTimeout(120000);
  const outbound: string[] = [],
    uploads: string[] = [];
  context.on("request", (request) => {
    if (
      request.url().startsWith("http") &&
      !request.url().startsWith("http://127.0.0.1:5173")
    )
      outbound.push(request.url());
    if (request.method() === "POST") uploads.push(request.url());
  });
  await photoMode(page);
  await page
    .getByLabel("정면 전신 사진", { exact: true })
    .setInputFiles("e2e/fixtures/full-body.jpg");
  await page
    .getByRole("button", { name: "MediaPipe 분석", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "33개 특징점을 추출했습니다" }),
  ).toBeVisible({ timeout: 100000 });
  await expect(page.getByAltText("정면 전신 사진 미리보기")).toHaveCount(0);
  await expect(
    page.getByRole("img", { name: /MediaPipe가 추출한 33개/ }),
  ).toBeVisible();
  const shoulder = Number(
    await page.getByRole("spinbutton", { name: /^어깨너비/ }).inputValue(),
  );
  expect(shoulder).toBeGreaterThan(20);
  expect(shoulder).toBeLessThan(65);
  await page.getByRole("spinbutton", { name: /^키/ }).fill("185");
  const scaled = Number(
    await page.getByRole("spinbutton", { name: /^어깨너비/ }).inputValue(),
  );
  expect(scaled / shoulder).toBeCloseTo(185 / 175, 2);
  await page.getByRole("spinbutton", { name: /^팔 길이/ }).fill("60");
  await page.getByRole("spinbutton", { name: /^키/ }).fill("180");
  await expect(page.getByRole("spinbutton", { name: /^팔 길이/ })).toHaveValue(
    "60",
  );
  await page
    .getByRole("button", { name: "체형 저장 (이 탭)", exact: true })
    .click();
  await page
    .getByRole("button", { name: "수동 입력 체형", exact: true })
    .click();
  await expect(page.getByRole("spinbutton", { name: /^키/ })).toHaveValue("");
  await page.getByRole("spinbutton", { name: /^키/ }).fill("160");
  await page.getByRole("spinbutton", { name: /^허리둘레/ }).fill("65");
  await page
    .getByRole("button", { name: "사진 분석 체형", exact: true })
    .click();
  await expect(page.getByRole("spinbutton", { name: /^키/ })).toHaveValue(
    "180",
  );
  await expect(page.getByRole("spinbutton", { name: /^허리둘레/ })).toHaveValue(
    "",
  );
  await page
    .getByRole("button", { name: "수동 입력 체형", exact: true })
    .click();
  await expect(page.getByRole("spinbutton", { name: /^허리둘레/ })).toHaveValue(
    "65",
  );
  await expect(
    page.getByRole("status").filter({ hasText: "3D 준비 완료" }),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `test-results/body-${testInfo.project.name}.png`,
    fullPage: true,
  });
  expect(outbound).toEqual([]);
  expect(uploads).toEqual([]);
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
});

test("실제 MediaPipe 인식 실패와 잘린 전신 사진을 안내하고 재시도한다", async ({
  page,
}) => {
  test.setTimeout(120000);
  await photoMode(page);
  const empty = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 300;
    canvas.height = 500;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "white";
    ctx.fillRect(0, 0, 300, 500);
    return canvas.toDataURL("image/png").split(",")[1];
  });
  await page.getByLabel("정면 전신 사진", { exact: true }).setInputFiles({
    name: "blank.png",
    mimeType: "image/png",
    buffer: Buffer.from(empty, "base64"),
  });
  await page
    .getByRole("button", { name: "MediaPipe 분석", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "사람을 찾지 못했습니다",
    { timeout: 100000 },
  );
  const data = (await readFile("e2e/fixtures/full-body.jpg")).toString(
    "base64",
  );
  const crop = await page.evaluate(async (base64) => {
    const image = new Image();
    image.src = `data:image/jpeg;base64,${base64}`;
    await image.decode();
    const canvas = document.createElement("canvas");
    canvas.width = image.width;
    canvas.height = Math.floor(image.height * 0.65);
    canvas.getContext("2d")!.drawImage(image, 0, 0);
    return canvas.toDataURL("image/png").split(",")[1];
  }, data);
  await page.getByLabel("정면 전신 사진", { exact: true }).setInputFiles({
    name: "cropped.png",
    mimeType: "image/png",
    buffer: Buffer.from(crop, "base64"),
  });
  await page
    .getByRole("button", { name: "MediaPipe 분석", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    /관절 일부|잘렸을|여백|비율을 안정적|사람을 찾지/,
    { timeout: 100000 },
  );
  await expect(
    page.getByRole("button", { name: "MediaPipe 분석", exact: true }),
  ).toBeEnabled();
});

test("실제 3D 렌더링·시점·줌·드래그·치수 갱신·초기화", async ({ page }) => {
  await page.goto("/#/mannequin");
  await expect(
    page.getByRole("status").filter({ hasText: "3D 준비 완료" }),
  ).toBeVisible({ timeout: 30000 });
  const canvas = page.locator("canvas");
  const before = await canvas.screenshot();
  await page.getByRole("button", { name: "측면", exact: true }).click();
  await expect
    .poll(async () => (await canvas.screenshot()).equals(before))
    .toBe(false);
  const side = await canvas.screenshot();
  await page.getByRole("button", { name: "후면", exact: true }).click();
  await expect
    .poll(async () => (await canvas.screenshot()).equals(side))
    .toBe(false);
  await page.getByRole("button", { name: "정면", exact: true }).click();
  const front = await canvas.screenshot();
  await page.getByRole("button", { name: "마네킹 확대", exact: true }).click();
  await expect
    .poll(async () => (await canvas.screenshot()).equals(front))
    .toBe(false);
  const zoomed = await canvas.screenshot();
  await page.getByRole("button", { name: "마네킹 축소", exact: true }).click();
  await expect
    .poll(async () => (await canvas.screenshot()).equals(zoomed))
    .toBe(false);
  const beforeDrag = await canvas.screenshot();
  const box = await canvas.boundingBox();
  expect(box).not.toBeNull();
  await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
  await page.mouse.down();
  await page.mouse.move(box!.x + box!.width * 0.75, box!.y + box!.height / 2, {
    steps: 8,
  });
  await page.mouse.up();
  await expect
    .poll(async () => (await canvas.screenshot()).equals(beforeDrag))
    .toBe(false);
  const beforeEdit = await canvas.screenshot();
  const viewport = page.getByRole("region", { name: "개인화 3D 마네킹" });
  await page.getByRole("spinbutton", { name: /^키/ }).fill("180");
  await page.getByRole("spinbutton", { name: /^허리둘레/ }).fill("110");
  await expect(viewport).toHaveAttribute(
    "data-body-revision",
    /^180\/.*\/110\//,
  );
  await expect
    .poll(async () => (await canvas.screenshot()).equals(beforeEdit))
    .toBe(false);
  await page
    .getByRole("button", { name: "체형 저장 (이 탭)", exact: true })
    .click();
  await page
    .getByRole("link", { name: "저장한 체형으로 스튜디오 이동", exact: true })
    .click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "3D 피팅 스튜디오",
  );
  await expect(
    page.getByRole("region", { name: "개인화 3D 피팅" }),
  ).toHaveAttribute("data-body-revision", /^180\/.*\/110\//);
  await page.goBack();
  await page
    .getByRole("button", { name: "기본 마네킹으로 초기화", exact: true })
    .click();
  await expect(page.getByRole("spinbutton", { name: /^키/ })).toHaveValue("");
});

test("암호화 기기 저장·새로고침 복원·잘못된 암호 차단·기기 삭제", async ({
  page,
}) => {
  await page.goto("/#/body");
  await page.getByRole("spinbutton", { name: /^키/ }).fill("173");
  await page.getByRole("spinbutton", { name: /^가슴둘레/ }).fill("93");
  await page
    .getByRole("button", { name: "체형 저장 (이 탭)", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "보관함 이름", exact: true })
    .fill("private-vault");
  await page
    .getByLabel("보관함 암호 (12자 이상)", { exact: true })
    .fill("test-password-12345");
  await page
    .getByRole("button", { name: "이 기기에 저장", exact: true })
    .click();
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "두 체형을 이 기기에 암호화 저장" }),
  ).toBeVisible();
  const raw = await page.evaluate(() => JSON.stringify(localStorage));
  expect(raw).not.toContain("test-password-12345");
  expect(raw).not.toContain("private-vault");
  expect(raw).not.toContain('"height"');
  await page.reload();
  await expect(page.getByRole("spinbutton", { name: /^키/ })).toHaveValue("");
  await page
    .getByRole("textbox", { name: "보관함 이름", exact: true })
    .fill("private-vault");
  await page
    .getByLabel("보관함 암호 (12자 이상)", { exact: true })
    .fill("wrong-password-123");
  await page
    .getByRole("button", { name: "보관함 불러오기", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("이름·암호가 다르거나");
  await page
    .getByLabel("보관함 암호 (12자 이상)", { exact: true })
    .fill("test-password-12345");
  await page
    .getByRole("button", { name: "보관함 불러오기", exact: true })
    .click();
  await expect(page.getByRole("spinbutton", { name: /^키/ })).toHaveValue(
    "173",
  );
  await page
    .getByLabel("보관함 암호 (12자 이상)", { exact: true })
    .fill("test-password-12345");
  await page
    .getByRole("button", { name: "기기 저장 삭제", exact: true })
    .click();
  await page
    .getByRole("button", { name: "보관함 삭제 확인", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "체형 보관함을 삭제했습니다" }),
  ).toBeVisible();
  await expect.poll(() => page.evaluate(() => localStorage.length)).toBe(0);
  await page
    .getByRole("button", { name: "현재 체형 삭제", exact: true })
    .click();
  await expect(page.getByRole("spinbutton", { name: /^키/ })).toHaveValue("");
});
