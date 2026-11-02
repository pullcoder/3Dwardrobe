import { mkdir, writeFile } from "node:fs/promises";
// 제품 데이터가 아닌 MediaPipe 공식 회귀 테스트 사진. 앱에는 포함·노출하지 않는다.
const source =
  "https://storage.googleapis.com/mediapipe-assets/male_full_height_hands.jpg";
const output = new URL("../e2e/fixtures/", import.meta.url);
await mkdir(output, { recursive: true });
const response = await fetch(source);
if (!response.ok)
  throw new Error(`테스트 사진 다운로드 실패: ${response.status}`);
await writeFile(
  new URL("full-body.jpg", output),
  Buffer.from(await response.arrayBuffer()),
);
console.log("MediaPipe 공식 테스트 사진 준비 완료 (Git 제외).");
