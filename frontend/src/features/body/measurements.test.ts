import { describe, expect, test } from "vitest";
import {
  createBodyProfiles,
  profileFromPose,
  applyHeight,
  summarizePose,
  validateMeasurements,
} from "./measurements";
import { createTorsoGeometry } from "../mannequin/geometry";
import type { Landmark } from "./types";

function fullBody() {
  const points: Landmark[] = Array.from({ length: 33 }, () => ({
    x: 0.5,
    y: 0.5,
    z: 0,
    visibility: 0.99,
  }));
  points[0] = { ...points[0], x: 0.5, y: 0.13 };
  const positions: Record<number, [number, number]> = {
    11: [0.35, 0.25],
    12: [0.65, 0.25],
    13: [0.29, 0.4],
    14: [0.71, 0.4],
    15: [0.25, 0.55],
    16: [0.75, 0.55],
    23: [0.4, 0.55],
    24: [0.6, 0.55],
    25: [0.4, 0.72],
    26: [0.6, 0.72],
    27: [0.4, 0.89],
    28: [0.6, 0.89],
    29: [0.4, 0.91],
    30: [0.6, 0.91],
    31: [0.4, 0.93],
    32: [0.6, 0.93],
  };
  for (const [index, [x, y]] of Object.entries(positions))
    points[Number(index)] = { x, y, z: 0, visibility: 0.99 };
  return points;
}
describe("치수 출처와 품질 경계", () => {
  test("키 변경은 추정 길이만 갱신한다", () => {
    const summary = summarizePose([fullBody()], 600, 1000);
    let profile = profileFromPose(summary, "170");
    expect(profile.values.chest).toBe("");
    profile = {
      ...profile,
      values: { ...profile.values, arm: "58" },
      origins: { ...profile.origins, arm: "user_entered" },
    };
    const next = applyHeight(profile, "187");
    expect(
      Number(next.values.shoulder) / Number(profile.values.shoulder),
    ).toBeCloseTo(1.1, 2);
    expect(next.values.arm).toBe("58");
    expect(next.origins.shoulder).toBe("estimated");
    expect(next.origins.arm).toBe("user_entered");
  });
  test("종횡비를 보정한 픽셀 거리 사용", () => {
    const points = fullBody(),
      ratio = summarizePose([points], 600, 1000);
    expect(ratio.shoulder).toBeGreaterThan(0.15);
    expect(ratio.shoulder).toBeLessThan(0.25);
  });
  test("잘린 신체와 낮은 가시성을 거절한다", () => {
    const cropped = fullBody();
    cropped[31].y = 1.1;
    expect(() => summarizePose([cropped], 600, 1000)).toThrow(/잘렸/);
    const hidden = fullBody();
    hidden[27].visibility = 0.2;
    expect(() => summarizePose([hidden], 600, 1000)).toThrow(/관절 일부/);
    expect(() => summarizePose([], 600, 1000)).toThrow(/사람을 찾지/);
    expect(() => summarizePose([fullBody(), fullBody()], 600, 1000)).toThrow(
      /두 명/,
    );
  });
  test("키와 관계없는 불가능한 길이 저장을 막는다", () => {
    const profile = createBodyProfiles().manual;
    expect(
      validateMeasurements({ ...profile.values, height: "170", leg: "140" }),
    ).toMatch(/너무 깁니다/);
    expect(validateMeasurements({ ...profile.values, height: "NaN" })).toMatch(
      /범위/,
    );
  });
  test("둘레 수정은 실제 torso 메시 크기를 변경한다", () => {
    const profile = createBodyProfiles().manual;
    const before = createTorsoGeometry(profile),
      after = createTorsoGeometry({
        ...profile,
        values: { ...profile.values, waist: "180" },
      });
    before.computeBoundingBox();
    after.computeBoundingBox();
    expect(after.boundingBox!.max.x).toBeGreaterThan(before.boundingBox!.max.x);
    expect(
      [...after.getAttribute("position").array].every(Number.isFinite),
    ).toBe(true);
    before.dispose();
    after.dispose();
  });
});
