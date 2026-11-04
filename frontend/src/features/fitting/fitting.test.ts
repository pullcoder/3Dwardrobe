import { describe, expect, it } from "vitest";
import {
  Box3,
  CylinderGeometry,
  Group,
  Mesh,
  MeshStandardMaterial,
  Vector3,
} from "three";
import { fitGarment } from "./fitting";
import { defaultAdjustment } from "../../types/fitting";
import type { FittingResource } from "../../types/fitting";
import { blankInfo } from "../garments/types";
import type { BodyProfile } from "../body/types";

const profile: BodyProfile = {
  values: {
    height: "170",
    shoulder: "40",
    chest: "90",
    waist: "75",
    hip: "94",
    arm: "55",
    leg: "80",
  },
  origins: {},
};
function model() {
  const group = new Group();
  const body = new Mesh(
    new CylinderGeometry(0.19, 0.24, 0.68, 16, 5, true).translate(0, 0.34, 0),
    new MeshStandardMaterial({ side: 2 }),
  );
  body.name = "body";
  group.add(body);
  return group;
}
function resource(mode: "A" | "B" = "A"): FittingResource {
  return {
    garment_id: "test",
    model_asset_id: "asset",
    rights_version: 1,
    name: "테스트 의류",
    category: "top",
    reconstruction_mode: mode,
    status: "available",
    info: {
      ...blankInfo,
      name: "테스트",
      garment_type: "티셔츠",
      measurements: [
        {
          label: "가슴단면",
          value: 50,
          unit: "cm",
          kind: "flat",
          target: "garment",
          source: "user_entered",
          size: null,
        },
      ],
    },
    metadata: {
      category: "top",
      garment_type: "티셔츠",
      unit: "meter",
      coordinate_system: "y_up_z_front",
      bounds: { min: [-0.24, 0, -0.24], max: [0.24, 0.68, 0.24] },
      dimensions: {
        length: { value: 0.68, source: "user_entered" },
        width: { value: 0.52, source: "estimated" },
      },
      mode,
      version: "stylefit-template-1.0",
      created_at: "2026-11-03",
      back_geometry: "estimated",
      warnings: [],
      triangle_count: 160,
      mesh_names: ["body"],
      physical_simulation: false,
    },
  };
}
describe("실제 3D 메시의 시각적 근사 피팅", () => {
  it("템플릿 계약을 붙인 AI 메시도 자동 착용하지 않는다", () => {
    const ai = resource();
    ai.metadata.engine = "triposr";
    ai.metadata.generation_kind = "ai";
    expect(() => fitGarment(model(), ai, profile, defaultAdjustment)).toThrow(
      /호환성/,
    );
  });
  it("원본을 보존하고 미터 좌표의 마네킹 몸통 위치로 장착한다", () => {
    const source = model(),
      before = source.children[0] as Mesh;
    const bytes = [...before.geometry.getAttribute("position").array];
    const fitted = fitGarment(source, resource(), profile, defaultAdjustment);
    const bounds = new Box3().setFromObject(fitted.group);
    expect(bounds.min.y).toBeGreaterThan(0.5);
    expect(bounds.max.y).toBeLessThan(1.7);
    expect(bounds.getSize(new Vector3()).z).toBeGreaterThan(0.1);
    expect([...before.geometry.getAttribute("position").array]).toEqual(bytes);
    expect(fitted.report.precise).toBe(false);
  });
  it("가슴과 어깨 조정은 전체 일괄 스케일 대신 정점에 서로 다르게 적용한다", () => {
    const source = model();
    const fitted = fitGarment(source, resource(), profile, defaultAdjustment);
    const changed = fitGarment(
      source,
      resource(),
      {
        ...profile,
        values: { ...profile.values, chest: "115", shoulder: "48" },
      },
      { ...defaultAdjustment, chest: 1.12 },
    );
    const a = (fitted.group.children[0] as Mesh).geometry.getAttribute(
      "position",
    );
    const b = (changed.group.children[0] as Mesh).geometry.getAttribute(
      "position",
    );
    const ratios = Array.from({ length: a.count }, (_, i) =>
      Math.abs(a.getX(i)) > 0.02 ? b.getX(i) / a.getX(i) : 1,
    ).map((r) => r.toFixed(2));
    expect(new Set(ratios).size).toBeGreaterThan(3);
    expect([...b.array].every(Number.isFinite)).toBe(true);
  });
  it("신체 치수와 의류 단면/단위를 구분하고 A/B에 같은 변형을 사용한다", () => {
    const a = fitGarment(model(), resource("A"), profile, defaultAdjustment);
    const b = fitGarment(model(), resource("B"), profile, defaultAdjustment);
    expect([
      ...(a.group.children[0] as Mesh).geometry.getAttribute("position").array,
    ]).toEqual([
      ...(b.group.children[0] as Mesh).geometry.getAttribute("position").array,
    ]);
    const input = resource();
    input.info.measurements[0].target = "body";
    expect(
      fitGarment(model(), input, profile, defaultAdjustment).report.status,
    ).toBe("insufficient");
  });
  it("지원하지 않는 좌표계와 부위 계약은 왜곡 없이 거절한다", () => {
    const input = resource();
    input.metadata.version = "unknown";
    expect(() =>
      fitGarment(model(), input, profile, defaultAdjustment),
    ).toThrow("호환성 오류");
    const source = model();
    source.children[0].name = "unknown_part";
    expect(() =>
      fitGarment(source, resource(), profile, defaultAdjustment),
    ).toThrow("호환성 오류");
  });
  it("실제 내부 메시의 방사선 교차를 검사하고 보정 상한 및 잔여를 보고한다", () => {
    const inner = fitGarment(model(), resource(), profile, {
      ...defaultAdjustment,
      chest: 1.25,
      waist: 1.25,
    });
    const outerResource = resource();
    outerResource.category = "outer";
    outerResource.info = { ...outerResource.info, category: "outer" };
    outerResource.metadata = { ...outerResource.metadata, category: "outer" };
    const result = fitGarment(
      model(),
      outerResource,
      profile,
      { ...defaultAdjustment, chest: 0.8, waist: 0.8 },
      [inner.group],
    );
    expect(result.report.layer_penetrations_before).toBeGreaterThan(0);
    expect(result.report.layer_penetrations_after).toBeLessThanOrEqual(
      result.report.layer_penetrations_before,
    );
    expect(result.report.max_correction_m).toBeLessThanOrEqual(0.05);
    expect(
      result.report.warnings.some((text) => text.includes("정밀 피팅 미지원")),
    ).toBe(true);
  });
});
