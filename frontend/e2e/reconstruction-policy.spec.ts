import { expect, test } from "@playwright/test";

test("A 기본 임시 등록 → 사진 비보관 재조회 → B 참조 접수와 우회 차단", async ({
  page,
}, testInfo) => {
  await page.goto("/#/upload");
  const username = `rights_${Date.now()}_${testInfo.project.name}`;
  const password = "rights-policy-test-password";
  await page.getByLabel("계정명", { exact: true }).fill(username);
  await page.getByLabel("암호", { exact: true }).fill(password);
  await page.getByLabel("계정 작업").selectOption("register");
  const registered = page.waitForResponse("**/auth/register");
  await page.getByRole("button", { name: "계정 만들기", exact: true }).click();
  const { token } = await (await registered).json();
  await page.getByRole("checkbox", { name: /직접 촬영/ }).check();
  await page
    .getByRole("combobox", { name: "사진 출처", exact: true })
    .selectOption("self_photographed");
  await expect(
    page.getByRole("checkbox", { name: /선택한 원본·누끼도/ }),
  ).not.toBeChecked();
  await expect(page.getByRole("button", { name: /B모드 ·/ })).toBeDisabled();
  const photo = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 120;
    canvas.height = 160;
    canvas.getContext("2d")!.fillRect(0, 0, 120, 160);
    return canvas.toDataURL("image/png").split(",")[1];
  });
  await page
    .getByLabel("앞면 사진", { exact: true })
    .setInputFiles({
      name: "shirt.png",
      mimeType: "image/png",
      buffer: Buffer.from(photo, "base64"),
    });
  await page
    .getByRole("textbox", { name: "의류 이름 필수", exact: true })
    .fill("권한 정책 테스트 의류");
  await page
    .getByRole("checkbox", { name: /분석·수정 정보와 복원 정책을/ })
    .check();
  const saved = page.waitForResponse(
    (r) => r.url().endsWith("/garments") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "디지털 옷장에 저장", exact: true })
    .click();
  const response = await saved;
  expect(response.status()).toBe(201);
  const garment = await response.json();
  expect(garment.assets).toEqual({});
  expect(garment.rights_status).toBe("unverified");
  expect(garment.reconstruction_mode).toBe("A");
  await page.getByRole("link", { name: /옷장에서 확인하기/ }).click();
  await page.reload();
  await page.getByLabel("계정명", { exact: true }).fill(username);
  await page.getByLabel("암호", { exact: true }).fill(password);
  await page.getByRole("button", { name: "로그인", exact: true }).click();
  await page
    .getByRole("button", { name: "저장된 옷장 불러오기", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "권한 정책 테스트 의류", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("원본 사진 비보관")).toBeVisible();
  await page
    .getByRole("button", { name: "상세 보기 / 수정", exact: true })
    .click();
  await page
    .getByLabel("권리 증빙 참조", { exact: true })
    .fill("이용허락 문서 참조 DOC-123");
  await page
    .getByRole("button", { name: "B모드 권한 검토 요청", exact: true })
    .click();
  await expect(
    page.getByText(/복원 모드: A · 권한 상태: 검토 중/),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "B모드 권한 검토 요청", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: /B모드 고정밀/ }),
  ).toBeDisabled();
  const forged = await page.request.patch(
    `http://127.0.0.1:8000/api/v1/garments/${garment.id}`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        info: garment.info,
        revision: 2,
        reconstruction_mode: "B",
        rights_status: "approved",
      },
    },
  );
  expect(forged.status()).toBe(400);
  const deleted = await page.request.delete(
    "http://127.0.0.1:8000/api/v1/auth/account",
    {
      headers: { Authorization: `Bearer ${token}` },
      data: { username, password },
    },
  );
  expect(deleted.status()).toBe(204);
});
