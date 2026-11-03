import * as THREE from "three";
import type { BodyProfile } from "../body/types";
import { resolvedBody } from "../body/measurements";

export const mannequinParts = [
  "head",
  "neck",
  "torso",
  "pelvis",
  "upper_arm_l",
  "forearm_l",
  "hand_l",
  "upper_arm_r",
  "forearm_r",
  "hand_r",
  "thigh_l",
  "calf_l",
  "foot_l",
  "thigh_r",
  "calf_r",
  "foot_r",
] as const;
export type MannequinPart = (typeof mannequinParts)[number];
export function bodyDimensions(profile: BodyProfile) {
  const values = resolvedBody(profile);
  const h = values.height / 100;
  // 불완전한 입력에서도 렌더링 가능한 중립 구조를 유지한다. 실측 복원이 아니다.
  const ankle = h * 0.045;
  const hip = THREE.MathUtils.clamp(
    values.leg / 100 + ankle,
    h * 0.12,
    h * 0.68,
  );
  const shoulder = h * 0.835;
  const waist = hip + (shoulder - hip) * 0.28;
  const chest = hip + (shoulder - hip) * 0.72;
  return {
    values,
    h,
    ankle,
    hip,
    waist,
    chest,
    shoulder,
    width: values.shoulder / 100,
    arm: Math.min(values.arm / 100, h * 0.48),
  };
}

export function ellipseRadius(circumferenceCm: number, depthRatio = 0.72) {
  // 라마누잔 타원 둘레 근사. 깊이/너비는 관측되지 않은 설계 가정이다.
  const unit =
    Math.PI *
    (3 * (1 + depthRatio) - Math.sqrt((3 + depthRatio) * (1 + 3 * depthRatio)));
  return circumferenceCm / 100 / unit;
}

export function createTorsoGeometry(profile: BodyProfile) {
  const d = bodyDimensions(profile),
    n = 48;
  const rings = [
    { y: d.hip - d.h * 0.055, rx: ellipseRadius(d.values.hip) * 0.72 },
    { y: d.hip, rx: ellipseRadius(d.values.hip) },
    { y: d.waist, rx: ellipseRadius(d.values.waist) },
    { y: d.chest, rx: ellipseRadius(d.values.chest) },
    { y: d.shoulder - d.h * 0.025, rx: d.width * 0.46 },
    { y: d.shoulder + d.h * 0.005, rx: d.width * 0.3 },
  ];
  const positions: number[] = [],
    indices: number[] = [];
  for (const ring of rings)
    for (let i = 0; i <= n; i++) {
      const angle = (i / n) * Math.PI * 2;
      positions.push(
        Math.cos(angle) * ring.rx,
        ring.y,
        Math.sin(angle) * ring.rx * 0.72,
      );
    }
  for (let j = 0; j < rings.length - 1; j++)
    for (let i = 0; i < n; i++) {
      const a = j * (n + 1) + i,
        b = a + n + 1;
      indices.push(a, b, a + 1, a + 1, b, b + 1);
    }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(positions, 3),
  );
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}
