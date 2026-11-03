import { emptyMeasurements, measurementFields } from "../../types/domain";
import type { Measurements } from "../../types/domain";
import { defaultBody } from "./types";
import type { BodyProfile, BodyProfiles, Landmark, PoseSummary } from "./types";

export function createBodyProfiles(): BodyProfiles {
  return {
    manual: { values: { ...emptyMeasurements }, origins: {} },
    photo: { values: { ...emptyMeasurements }, origins: {} },
  };
}

export function validateMeasurements(values: Measurements): string | null {
  for (const field of measurementFields) {
    const raw = values[field.key];
    if (raw === "") continue;
    const value = Number(raw);
    if (!Number.isFinite(value) || value < field.min || value > field.max)
      return `${field.label}는 ${field.min}~${field.max} cm 범위로 입력해 주세요.`;
  }
  const h = Number(values.height || defaultBody.height);
  if (values.leg && Number(values.leg) > h * 0.62)
    return "다리 길이(골반 관절~발목)가 키에 비해 너무 깁니다. 측정 기준을 확인해 주세요.";
  if (values.arm && Number(values.arm) > h * 0.48)
    return "팔 길이(어깨 관절~손목)가 키에 비해 너무 깁니다. 측정 기준을 확인해 주세요.";
  return null;
}

export function resolvedBody(profile: BodyProfile) {
  const h = Number(profile.values.height || defaultBody.height);
  const scale = Number.isFinite(h) && h >= 80 && h <= 250 ? h / 170 : 1;
  return Object.fromEntries(
    measurementFields.map(({ key, min, max }) => {
      const value = Number(profile.values[key]);
      const fallback = defaultBody[key] * scale;
      return [
        key,
        profile.values[key] !== "" &&
        Number.isFinite(value) &&
        value >= min &&
        value <= max
          ? value
          : fallback,
      ];
    }),
  ) as Record<keyof Measurements, number>;
}

export function applyHeight(profile: BodyProfile, height: string): BodyProfile {
  const next = {
    ...profile,
    values: { ...profile.values, height },
    origins: { ...profile.origins, height: "user_entered" as const },
    saved_at: undefined,
  };
  if (!profile.ratios || !height || Number(height) < 80 || Number(height) > 250)
    return next;
  for (const key of ["shoulder", "arm", "leg"] as const) {
    if (profile.origins[key] !== "user_entered") {
      next.values[key] = (profile.ratios[key] * Number(height)).toFixed(1);
      next.origins[key] = "estimated";
    }
  }
  return next;
}

export function profileFromPose(
  summary: PoseSummary,
  height: string,
): BodyProfile {
  return applyHeight(
    { values: { ...emptyMeasurements, height }, origins: {}, ratios: summary },
    height,
  );
}

const required = [
  0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32,
];
export const poseConnections = [
  [11, 12],
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16],
  [11, 23],
  [12, 24],
  [23, 24],
  [23, 25],
  [25, 27],
  [24, 26],
  [26, 28],
  [27, 29],
  [29, 31],
  [28, 30],
  [30, 32],
];

export function summarizePose(
  poses: Landmark[][],
  width: number,
  height: number,
): PoseSummary {
  if (!poses.length)
    throw new Error(
      "사람을 찾지 못했습니다. 밝은 곳에서 전신이 보이는 사진으로 다시 시도해 주세요.",
    );
  if (poses.length > 1)
    throw new Error(
      "두 명 이상이 인식됐습니다. 본인 한 명만 나온 사진을 선택해 주세요.",
    );
  const points = poses[0];
  if (
    points.length !== 33 ||
    required.some(
      (i) =>
        !points[i] ||
        !Number.isFinite(points[i].x) ||
        !Number.isFinite(points[i].y) ||
        points[i].visibility < 0.55,
    )
  )
    throw new Error(
      "관절 일부가 가려졌거나 전신 인식이 불안정합니다. 손목·골반·무릎·발목이 보이는 정면 사진으로 다시 시도해 주세요.",
    );
  if (
    required.some(
      (i) =>
        points[i].x <= 0.015 ||
        points[i].x >= 0.985 ||
        points[i].y <= 0.015 ||
        points[i].y >= 0.985,
    )
  )
    throw new Error(
      "신체가 사진 가장자리에 닿거나 잘렸을 수 있습니다. 머리와 발끝 주변에 여백을 두고 다시 촬영해 주세요.",
    );
  const distance = (a: number, b: number) =>
    Math.hypot(
      (points[a].x - points[b].x) * width,
      (points[a].y - points[b].y) * height,
    );
  // 정수리 점이 없으므로 코~어깨 중심 거리의 0.6배를 코 위로 더한 경험적 높이다.
  const shoulderY = (points[11].y + points[12].y) / 2;
  const headTop = points[0].y - Math.abs(shoulderY - points[0].y) * 0.6;
  const footBottom = Math.max(...[29, 30, 31, 32].map((i) => points[i].y));
  if (headTop < 0.01)
    throw new Error(
      "머리 위 여백이 부족합니다. 정수리부터 발끝까지 들어오도록 촬영해 주세요.",
    );
  const span = (footBottom - headTop) * height;
  if (span / height < 0.35)
    throw new Error(
      "사진 속 사람이 너무 작습니다. 전신이 화면을 충분히 채우도록 촬영해 주세요.",
    );
  const shoulder = distance(11, 12) / span;
  const arm =
    (distance(11, 13) +
      distance(13, 15) +
      distance(12, 14) +
      distance(14, 16)) /
    2 /
    span;
  const leg =
    (distance(23, 25) +
      distance(25, 27) +
      distance(24, 26) +
      distance(26, 28)) /
    2 /
    span;
  const torso = (distance(11, 23) + distance(12, 24)) / 2 / span;
  if (
    shoulder < 0.12 ||
    shoulder > 0.4 ||
    arm < 0.15 ||
    arm > 0.48 ||
    leg < 0.25 ||
    leg > 0.62
  )
    throw new Error(
      "정면 체형 비율을 안정적으로 추정하기 어렵습니다. 몸을 곧게 세우고 팔을 몸에서 조금 띄워 다시 촬영해 주세요.",
    );
  return {
    shoulder,
    arm,
    leg,
    torso,
    mean_visibility:
      required.reduce((sum, i) => sum + points[i].visibility, 0) /
      required.length,
    method: "projected_2d_v1",
  };
}
