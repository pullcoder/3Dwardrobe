// 원본 GLB를 보존하고 지원되는 의미 부위의 정점만 변형하는 시각적 근사 피팅.
import { Group, Mesh, Raycaster, Vector3 } from "three";
import type { BufferAttribute } from "three";
import type { BodyProfile } from "../body/types";
import type { FitAdjustment, FittingResource } from "../../types/fitting";
import { bodyDimensions, ellipseRadius } from "../mannequin/geometry";

export interface FitReport {
  status: "visual" | "insufficient";
  precise: false;
  body_penetrations_before: number;
  body_penetrations_after: number;
  layer_penetrations_before: number;
  layer_penetrations_after: number;
  max_correction_m: number;
  warnings: string[];
}
const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
function interpolate(y: number, points: number[][]) {
  if (y <= points[0][0]) return points[0][1];
  for (let i = 1; i < points.length; i++)
    if (y <= points[i][0]) {
      const [a, b] = [points[i - 1], points[i]];
      return a[1] + ((b[1] - a[1]) * (y - a[0])) / (b[0] - a[0]);
    }
  return points[points.length - 1][1];
}
export function fitGarment(
  source: Group,
  resource: FittingResource,
  profile: BodyProfile,
  adjustment: FitAdjustment,
  innerLayers: Group[] = [],
) {
  const meta = resource.metadata;
  if (
    meta.generation_kind === "ai" ||
    meta.engine === "triposr" ||
    meta.engine === "trellis2" ||
    meta.unit !== "meter" ||
    meta.coordinate_system !== "y_up_z_front" ||
    meta.category !== resource.category ||
    !(
      meta.fitting_contract === "stylefit.parts.v1" ||
      (meta.fitting_contract === "stylefit.panel.v3" &&
        !!meta.top_panel &&
        resource.category === "top") ||
      (meta.fitting_contract === "stylefit.pants.v2" &&
        resource.category === "bottom" &&
        !!meta.pants) ||
      meta.version === "stylefit-template-1.0"
    )
  )
    throw new Error(
      "모델 호환성 오류: 지원되는 부위별 피팅 계약이 없습니다. 임의로 변형하지 않습니다.",
    );
  const allowed = new Set([
    "body",
    "collar",
    "sleeve_left",
    "sleeve_right",
    "waist",
    "leg_left",
    "leg_right",
    "skirt",
  ]);
  let found = 0;
  source.traverse((object) => {
    if (
      object.position.lengthSq() > 1e-10 ||
      Math.abs(object.quaternion.w) < 1 - 1e-8 ||
      object.scale.distanceToSquared(new Vector3(1, 1, 1)) > 1e-10
    )
      throw new Error("모델 호환성 오류: 부위 좌표가 정규화되지 않았습니다.");
    if (object instanceof Mesh) {
      if (!allowed.has(object.name))
        throw new Error("모델 호환성 오류: 의미를 알 수 없는 메시 부위입니다.");
      found++;
    }
  });
  if (!found) throw new Error("모델 호환성 오류: 실제 메시가 없습니다.");
  const d = bodyDimensions(profile),
    dims = meta.dimensions;
  const value = (key: string, fallback: number) => dims[key]?.value ?? fallback;
  const height = value("length", 0.68),
    width = value("width", 0.52),
    sleeveLength = value("sleeve", 0.57);
  if (![height, width, sleeveLength].every((v) => Number.isFinite(v) && v > 0))
    throw new Error("모델 호환성 오류: 의류 크기를 확인해 주세요.");
  const hip = ellipseRadius(d.values.hip),
    chest = ellipseRadius(d.values.chest),
    waist = ellipseRadius(d.values.waist);
  const garmentMeasure = (labels: string[], kind: "flat" | "length") => {
    const sorted = [...resource.info.measurements].sort(
      (a, b) =>
        Number(a.source !== "user_entered") -
        Number(b.source !== "user_entered"),
    );
    const measurement = sorted.find(
      (m) =>
        labels.includes(m.label) &&
        m.kind === kind &&
        m.target === "garment" &&
        (!m.size ||
          m.size.trim().toLowerCase() ===
            resource.info.size.trim().toLowerCase()) &&
        m.value !== null &&
        m.unit !== "unknown",
    );
    if (!measurement || measurement.value === null) return null;
    const meters =
      measurement.value *
      { cm: 0.01, mm: 0.001, inch: 0.0254, unknown: 0 }[measurement.unit];
    if (
      !Number.isFinite(meters) ||
      meters <= 0 ||
      meters > (kind === "flat" ? 1 : 1.6)
    )
      throw new Error("치수 정보 부족: 의류 치수 범위와 단위를 확인해 주세요.");
    return meters;
  };
  const measuredChest = garmentMeasure(["가슴단면", "가슴너비"], "flat");
  const measuredWaist = garmentMeasure(["허리단면"], "flat");
  const measuredThigh = garmentMeasure(["허벅지단면"], "flat");
  const measuredShoulder =
    garmentMeasure(["어깨너비", "어깨길이"], "length") ??
    garmentMeasure(["어깨너비"], "flat");
  const measuredRise = garmentMeasure(["밑위"], "length");
  const missing =
    Object.values(profile.values).some((v) => v === "") ||
    (resource.category === "bottom" ? !measuredWaist : !measuredChest) ||
    dims.length?.source === "estimated";
  const report: FitReport = {
    status: missing ? "insufficient" : "visual",
    precise: false,
    body_penetrations_before: 0,
    body_penetrations_after: 0,
    layer_penetrations_before: 0,
    layer_penetrations_after: 0,
    max_correction_m: 0,
    warnings: [],
  };
  const margin = adjustment.clearance;
  // 단면×2로 추정 둘레를 만든 뒤 신체 타원과 비교한다. 신체 둘레를 단면 너비로 취급하지 않는다.
  const fromFlat = (flat: number) => ellipseRadius(flat * 200);
  const desiredChest =
    Math.max(
      chest + margin,
      measuredChest ? fromFlat(measuredChest) : chest * 1.09,
    ) * adjustment.chest;
  const desiredWaist =
    Math.max(
      waist + margin,
      measuredWaist ? fromFlat(measuredWaist) : waist * 1.1,
    ) * adjustment.waist;
  const desiredShoulder =
    Math.max(d.width, measuredShoulder ?? d.width) * adjustment.shoulder;
  const topHem =
    d.shoulder -
    (dims.length?.source === "estimated"
      ? resource.category === "outer" && resource.info.garment_type === "코트"
        ? d.h * 0.6
        : d.shoulder - d.hip + d.h * 0.065
      : height) *
      adjustment.length;
  const bottomLength =
    (dims.length?.source === "estimated"
      ? (d.waist - d.ankle) *
        (resource.info.garment_type === "반바지"
          ? 0.48 / 1.02
          : resource.info.garment_type === "스커트"
            ? 0.6 / 1.02
            : 1)
      : height) * adjustment.length;
  const bottomHem = d.waist - bottomLength;
  const waistY = clamp(
    d.waist,
    topHem + (d.shoulder - topHem) * 0.1,
    d.shoulder - (d.shoulder - topHem) * 0.3,
  );
  const chestY = clamp(
    d.chest,
    waistY + (d.shoulder - waistY) * 0.2,
    d.shoulder - (d.shoulder - waistY) * 0.1,
  );
  const crotch = measuredRise ? d.waist - measuredRise : d.hip;
  const group = source.clone(true);
  const capsules: { a: Vector3; b: Vector3; radius: number }[] = [];
  for (const sign of [-1, 1]) {
    const shoulder = new Vector3((sign * d.width) / 2, d.shoulder, 0);
    const elbow = new Vector3(
      sign * (d.width / 2 + d.arm * 0.11),
      d.shoulder - d.arm * 0.5,
      0,
    );
    const wrist = new Vector3(
      sign * (d.width / 2 + d.arm * 0.19),
      d.shoulder - d.arm * 0.98,
      0.015,
    );
    const hipPoint = new Vector3(sign * hip * 0.47, d.hip, 0);
    const knee = new Vector3(sign * hip * 0.49, (d.hip + d.ankle) / 2, 0.007);
    const ankle = new Vector3(sign * hip * 0.5, d.ankle, 0);
    capsules.push(
      { a: shoulder, b: elbow, radius: d.h * 0.023 },
      { a: elbow, b: wrist, radius: d.h * 0.019 },
      { a: hipPoint, b: knee, radius: hip * 0.4 },
      { a: knee, b: ankle, radius: d.h * 0.03 },
    );
  }
  const torsoRadii = (y: number): [number, number] | null => {
    if (y < d.hip - d.h * 0.1 || y > d.shoulder + d.h * 0.005) return null;
    let rx = interpolate(y, [
      [d.hip - d.h * 0.055, hip * 0.72],
      [d.hip, hip],
      [d.waist, waist],
      [d.chest, chest],
      [d.shoulder - d.h * 0.025, d.width * 0.46],
      [d.shoulder + d.h * 0.005, d.width * 0.3],
    ]);
    let rz = rx * 0.72;
    const py = (y - (d.hip - d.h * 0.035)) / (d.h * 0.065);
    if (Math.abs(py) < 1) {
      rx = Math.max(rx, hip * 0.9 * Math.sqrt(1 - py * py));
      rz = Math.max(rz, hip * 0.65 * Math.sqrt(1 - py * py));
    }
    return [rx, rz];
  };
  function penetration(point: Vector3) {
    const surface = torsoRadii(point.y);
    if (surface) {
      const [rx, rz] = surface;
      const radial = Math.sqrt((point.x / rx) ** 2 + (point.z / rz) ** 2);
      if (radial < 1)
        return new Vector3(point.x, 0, point.z)
          .multiplyScalar(1 / Math.max(radial, 0.001))
          .sub(new Vector3(point.x, 0, point.z));
    }
    for (const capsule of capsules) {
      const delta = capsule.b.clone().sub(capsule.a);
      const closest = delta
        .multiplyScalar(
          clamp(
            point.clone().sub(capsule.a).dot(delta) / delta.lengthSq(),
            0,
            1,
          ),
        )
        .add(capsule.a);
      const normal = point.clone().sub(closest),
        distance = normal.length();
      if (distance < capsule.radius)
        return normal
          .normalize()
          .multiplyScalar(capsule.radius - distance + 0.002);
    }
    return null;
  }
  const raycaster = new Raycaster(),
    radial = new Vector3(),
    origin = new Vector3();
  for (const inner of innerLayers) inner.updateMatrixWorld(true);
  group.traverse((object) => {
    if (!(object instanceof Mesh)) return;
    object.geometry = object.geometry.clone();
    const attribute = object.geometry.getAttribute(
      "position",
    ) as BufferAttribute;
    const sign = object.name.endsWith("left") ? -1 : 1;
    const layerTargets: Mesh[] = [];
    for (const inner of innerLayers)
      inner.traverse((part) => {
        if (
          part instanceof Mesh &&
          (object.name.startsWith("sleeve")
            ? part.name === object.name
            : !part.name.startsWith("sleeve"))
        )
          layerTargets.push(part);
      });
    for (let i = 0; i < attribute.count; i++) {
      let x = attribute.getX(i),
        y = attribute.getY(i),
        z = attribute.getZ(i);
      const oldY = y;
      let sleeveOrigin: Vector3 | undefined;
      if (meta.fitting_contract === "stylefit.panel.v3" && meta.top_panel) {
        // 한 패널의 몸판/소매를 같은 연속 가중치로 변형해 어깨 경계가 갈라지지 않는다.
        const side = x < 0 ? -1 : 1;
        const joint = meta.top_panel.shoulder_half_width;
        const dx = Math.abs(x) - joint;
        const dy = oldY - height * 0.91;
        let weight = clamp(dx / (width * 0.18), 0, 1);
        weight *= clamp((oldY / height - 0.52) / 0.18, 0, 1);
        weight = weight * weight * (3 - 2 * weight);
        const angle = 0.85;
        const armScale = (d.arm / 0.55) * adjustment.sleeve;
        const armX =
          side *
          (desiredShoulder / 2 +
            (dx * Math.cos(angle) + dy * Math.sin(angle)) * armScale);
        const armY =
          d.shoulder -
          0.02 +
          (-dx * Math.sin(angle) + dy * Math.cos(angle)) * armScale;
        const torsoScale = Math.max(2 * (chest + margin), width * 0.78) / width;
        const shapeScale = interpolate(oldY / height, [
          [0, adjustment.hip],
          [0.4, adjustment.waist],
          [0.8, adjustment.chest],
          [1, adjustment.shoulder],
        ]);
        x = x * torsoScale * shapeScale * (1 - weight) + armX * weight;
        y =
          (topHem + (oldY / height) * (d.shoulder - topHem)) * (1 - weight) +
          armY * weight;
        z *= Math.max(1, (chest * 0.72 + margin) / 0.11);
        const surface = torsoRadii(y + adjustment.offset_y);
        if (surface && weight < 0.3) {
          const [rx, rz] = surface;
          const envelope =
            (rz + margin + 0.012) *
            Math.sqrt(Math.max(0, 1 - (x / (rx + margin + 0.012)) ** 2));
          z = Math.sign(z || 1) * Math.max(Math.abs(z), envelope);
        }
      } else if (object.name.startsWith("sleeve")) {
        const t = clamp(
          ((x - sign * width * 0.43) * sign * 0.52 +
            (height * 0.82 - y) * 0.85) /
            (sleeveLength * (0.52 ** 2 + 0.85 ** 2)),
          0,
          1,
        );
        const oldCx = sign * (width * 0.43 + sleeveLength * 0.52 * t),
          oldCy = height * 0.82 - sleeveLength * 0.85 * t;
        const radius =
          ((x - oldCx) * 0.85 + (y - oldCy) * sign * 0.52) /
          (0.85 ** 2 + 0.52 ** 2);
        const actualSleeve =
          (dims.sleeve?.source === "user_entered" ||
          dims.sleeve?.source === "ocr"
            ? sleeveLength
            : (sleeveLength * d.arm) / 0.55) * adjustment.sleeve;
        x =
          (sign * desiredShoulder) / 2 +
          sign * 0.19 * actualSleeve * t +
          0.98 * radius;
        y = d.shoulder - 0.98 * actualSleeve * t + sign * 0.19 * radius;
        z += 0.015 * t;
        sleeveOrigin = new Vector3(
          (sign * desiredShoulder) / 2 + sign * 0.19 * actualSleeve * t,
          d.shoulder - 0.98 * actualSleeve * t + adjustment.offset_y,
          0.015 * t,
        );
      } else if (meta.fitting_contract === "stylefit.pants.v2" && meta.pants) {
        // 사진의 넓은 밑단/낮은 밑위와 연결부를 보존한다. 고정 원통 중심으로 되돌리지 않는다.
        const t = clamp(oldY / height, 0, 1);
        const garmentWaist = value("waist_width", width);
        const garmentHip = value("hip_width", width * 1.3);
        const fitScale = Math.max(
          1,
          (2 * (waist + margin)) / garmentWaist,
          (2 * (hip + margin)) / garmentHip,
        );
        const userScale = interpolate(t, [
          [0, adjustment.hip],
          [1 - meta.pants.rise_ratio, adjustment.hip],
          [1, adjustment.waist],
        ]);
        x *= fitScale * userScale;
        z *=
          Math.max(1, (hip * 0.72 + margin) / (value("depth", 0.2) / 2)) *
          userScale;
        y = bottomHem + bottomLength * t;
        // 골반 곡면이 행 사이에서 돌출되지 않도록 앞뒤 패널에 보수적 여유를 둔다.
        // 사진의 x 외곽은 유지하고 관측되지 않은 깊이만 근사 보정한다.
        const surface = torsoRadii(y + adjustment.offset_y);
        if (surface) {
          const [rx, rz] = surface;
          const envelope =
            (rz + margin + 0.015) *
            Math.sqrt(Math.max(0, 1 - (x / (rx + margin + 0.015)) ** 2));
          z = Math.sign(z || 1) * Math.max(Math.abs(z), envelope);
        }
      } else if (object.name.startsWith("leg")) {
        const t = clamp(y / (height * 0.78), 0, 1);
        const oldCenter = sign * width * 0.25;
        const targetCenter = sign * hip * (0.5 - 0.03 * t) * adjustment.hip;
        const scale =
          Math.max(
            hip * 0.4 + margin,
            measuredThigh ? fromFlat(measuredThigh) : hip * 0.48,
          ) /
          (width * 0.26);
        x = targetCenter + (x - oldCenter) * scale;
        z *= Math.max(1, (d.h * 0.03 + margin) / (0.23 * 0.34));
        y = bottomHem + (crotch - bottomHem) * t;
      } else if (object.name === "waist" || object.name === "skirt") {
        const t = oldY / height;
        y =
          object.name === "skirt"
            ? bottomHem + bottomLength * t
            : crotch + ((d.waist - crotch) * (t - 0.73)) / 0.27;
        const bodyR =
          object.name === "skirt"
            ? hip * adjustment.hip
            : interpolate(t, [
                [0.73, hip * adjustment.hip],
                [1, desiredWaist],
              ]);
        const ratio = (bodyR + margin) / (width * 0.5);
        x *= ratio;
        z *= Math.max(ratio, (hip * 0.72 + margin) / (0.23 * 0.5));
      } else if (object.name === "collar") {
        y = d.shoulder + (oldY - height);
        x *= desiredShoulder / d.width;
      } else {
        const t = oldY / height;
        y = interpolate(t, [
          [0, topHem],
          [0.4, waistY],
          [0.78, chestY],
          [0.94, Math.max(chestY + 0.001, d.shoulder - d.h * 0.025)],
          [1, d.shoulder + d.h * 0.005],
        ]);
        const rx = interpolate(t, [
          [0, hip * adjustment.hip + margin],
          [0.4, desiredWaist],
          [0.78, desiredChest],
          [0.94, desiredShoulder * 0.5],
          [1, Math.min(0.1, desiredShoulder * 0.25)],
        ]);
        const originalRx = interpolate(t, [
          [0, width * (resource.info.garment_type === "코트" ? 0.65 : 0.54)],
          [0.4, width * 0.49],
          [0.78, width * 0.5],
          [0.94, width * 0.44],
          [1, Math.min(width * 0.19, 0.1)],
        ]);
        x *= rx / Math.max(originalRx, 0.02);
        z *= interpolate(t, [
          [0, (hip * 0.72 + margin) / 0.1152],
          [0.4, (waist * 0.72 + margin) / 0.12],
          [0.78, (chest * 0.72 + margin) / 0.12],
          [1, 1],
        ]);
      }
      const point = new Vector3(x, y + adjustment.offset_y, z);
      const correction = penetration(point);
      if (correction) {
        report.body_penetrations_before++;
        report.max_correction_m = Math.max(
          report.max_correction_m,
          Math.min(0.05, correction.length()),
        );
        point.add(correction.clampLength(0, 0.05));
      }
      if (innerLayers.length) {
        if (sleeveOrigin) {
          origin.copy(sleeveOrigin);
          radial.copy(point).sub(origin);
        } else {
          origin.set(0, point.y, 0);
          radial.set(point.x, 0, point.z);
        }
        const radius = radial.length();
        if (radius > 0.01) {
          raycaster.set(origin, radial.normalize());
          const hits = raycaster.intersectObjects(layerTargets, false);
          const required = hits.length
            ? Math.max(...hits.map((hit) => hit.distance)) + margin
            : 0;
          if (required > radius + 0.001) {
            report.layer_penetrations_before++;
            const correctionLength = Math.min(required - radius, 0.05);
            point.addScaledVector(radial, correctionLength);
            report.max_correction_m = Math.max(
              report.max_correction_m,
              correctionLength,
            );
            if (required - radius > 0.051) report.layer_penetrations_after++;
          }
        }
      }
      if (penetration(point)) report.body_penetrations_after++;
      if (![point.x, point.y, point.z].every(Number.isFinite))
        throw new Error("모델 호환성 오류: 정점 변형이 유효하지 않습니다.");
      attribute.setXYZ(i, point.x, point.y, point.z);
    }
    attribute.needsUpdate = true;
    object.geometry.computeVertexNormals();
    object.geometry.computeBoundingBox();
    object.geometry.computeBoundingSphere();
  });
  group.updateMatrixWorld(true);
  if (missing)
    report.warnings.push(
      "치수 정보 부족: 미입력 신체/의류 값에 기본 비율·추정치를 사용합니다.",
    );
  if (report.body_penetrations_after || report.layer_penetrations_after)
    report.warnings.push(
      "관통 잔여 가능성: 제한된 보정으로 해결되지 않은 지점이 있습니다.",
    );
  report.warnings.push(
    "정밀 피팅 미지원: 정점/단면 기반 근사 검사이며 모든 삼각형 교차·착용 압력·원단 거동을 보장하지 않습니다.",
  );
  return { group, report };
}
