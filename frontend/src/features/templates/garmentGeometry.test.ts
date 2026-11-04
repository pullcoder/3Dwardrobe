/// <reference types="node" />
import { afterAll, describe, expect, it } from "vitest";
import { mkdirSync, writeFileSync } from "node:fs";
import { Vector3, Raycaster, Mesh } from "three";
import { createBodyProfiles } from "../body/measurements";
import {
  defaultTemplateInput,
  physicalParameters,
  resolveTemplateInput,
  templateCatalog,
} from "./catalog";
import {
  createTemplateGarment,
  disposeTemplateGarment,
} from "./garmentGeometry";

const profile = createBodyProfiles().manual;
const validationRows: unknown[] = [];
afterAll(() => {
  if (process.env.STYLEFIT_TEMPLATE_REPORT !== "1") return;
  const directory = new URL(
    "../../../../backend/storage/template-validation/",
    import.meta.url,
  );
  mkdirSync(directory, { recursive: true });
  writeFileSync(
    new URL("metrics.json", directory),
    JSON.stringify(validationRows, null, 2),
  );
});
describe("입체 의류 템플릿", () => {
  for (const definition of templateCatalog)
    it(`${definition.name}: 유한 좌표·두께·UV·연결 면`, () => {
      const model = createTemplateGarment(
        defaultTemplateInput(definition.id),
        profile,
      );
      const position = model.geometry.getAttribute("position"),
        normal = model.geometry.getAttribute("normal"),
        uv = model.geometry.getAttribute("uv");
      const indices = model.geometry.index!;
      expect(model.stats.triangles).toBeGreaterThan(1000);
      expect(model.stats.triangles).toBeLessThan(12000);
      expect(
        model.geometry.boundingBox!.getSize(new Vector3()).z,
      ).toBeGreaterThan(0.1);
      expect(position.count).toBe(uv.count);
      expect(
        [...position.array, ...normal.array, ...uv.array].every(
          Number.isFinite,
        ),
      ).toBe(true);
      expect(Math.min(...uv.array)).toBeGreaterThanOrEqual(0);
      expect(Math.max(...uv.array)).toBeLessThanOrEqual(1);
      const a = new Vector3(),
        b = new Vector3(),
        c = new Vector3();
      let degenerate = 0;
      const edgeCount = new Map<string, number>();
      const edgeDirection = new Map<string, number>();
      for (let i = 0; i < indices.count; i += 3) {
        const ids = [indices.getX(i), indices.getX(i + 1), indices.getX(i + 2)];
        a.fromBufferAttribute(position, ids[0]);
        b.fromBufferAttribute(position, ids[1]);
        c.fromBufferAttribute(position, ids[2]);
        if (b.sub(a).cross(c.sub(a)).lengthSq() < 1e-19) degenerate++;
        for (let j = 0; j < 3; j++) {
          const x = ids[j],
            y = ids[(j + 1) % 3],
            key = x < y ? `${x}/${y}` : `${y}/${x}`;
          edgeCount.set(key, (edgeCount.get(key) ?? 0) + 1);
          edgeDirection.set(
            key,
            (edgeDirection.get(key) ?? 0) + (x < y ? 1 : -1),
          );
        }
      }
      expect(degenerate).toBe(0);
      // 두께의 안팎과 개구부 테두리는 닫힌 원단 셸. 내부 의복 공간을 덮는 캡은 없다.
      expect([...edgeCount.values()].every((count) => count === 2)).toBe(true);
      expect(
        [...edgeDirection.values()].every((direction) => direction === 0),
      ).toBe(true);
      expect(model.stats.openings).toBeGreaterThanOrEqual(3);
      expect(model.stats.parts).toContain(
        definition.category === "pants" ? "hips" : "sleeve_left",
      );
      validationRows.push({
        template: definition.id,
        name: definition.name,
        ...model.stats,
        bounds: {
          min: model.geometry.boundingBox!.min.toArray(),
          max: model.geometry.boundingBox!.max.toArray(),
        },
        buffer_bytes:
          position.array.byteLength +
          normal.array.byteLength +
          uv.array.byteLength +
          indices.array.byteLength,
        nonmanifold_edges: 0,
        inconsistent_winding_edges: 0,
        degenerate_triangles: degenerate,
        source: "project_original_reusable_mesh",
        unit: "meter",
      });
      expect(model.stats.parts).toContain(
        definition.category === "pants" ? "leg_right" : "collar",
      );
      const again = createTemplateGarment(
        defaultTemplateInput(definition.id),
        profile,
      );
      expect(again.stats.topologyReused).toBe(true);
      disposeTemplateGarment(again);
      disposeTemplateGarment(model);
    });
  it("모든 조절 값이 전체 배율 대신 실제 정점 일부를 변경한다", () => {
    for (const definition of templateCatalog)
      for (const parameter of definition.parameters) {
        const input = defaultTemplateInput(definition.id);
        input.parameters[parameter.key] = 0.1;
        const a = createTemplateGarment(input, profile);
        input.parameters[parameter.key] = 0.9;
        const b = createTemplateGarment(input, profile);
        const first = a.geometry.getAttribute("position"),
          second = b.geometry.getAttribute("position");
        let moved = 0,
          unchanged = 0;
        for (let i = 0; i < first.count; i++) {
          const delta = new Vector3()
            .fromBufferAttribute(first, i)
            .distanceTo(new Vector3().fromBufferAttribute(second, i));
          if (delta > 0.0001) moved++;
          else unchanged++;
        }
        expect(moved, `${definition.id}.${parameter.key}`).toBeGreaterThan(20);
        expect(unchanged, `${definition.id}.${parameter.key}`).toBeGreaterThan(
          10,
        );
        disposeTemplateGarment(a);
        disposeTemplateGarment(b);
      }
  });
  it("정규화 최솟값·최댓값 조합에서도 퇴화면이나 비정상 좌표가 없다", () => {
    for (const definition of templateCatalog)
      for (const endpoint of [0, 1]) {
        const input = defaultTemplateInput(definition.id);
        for (const key of Object.keys(input.parameters))
          input.parameters[key] = endpoint;
        const model = createTemplateGarment(input, profile),
          p = model.geometry.getAttribute("position"),
          ids = model.geometry.index!;
        expect([...p.array].every(Number.isFinite)).toBe(true);
        const a = new Vector3(),
          b = new Vector3(),
          c = new Vector3();
        for (let i = 0; i < ids.count; i += 3) {
          a.fromBufferAttribute(p, ids.getX(i));
          b.fromBufferAttribute(p, ids.getX(i + 1));
          c.fromBufferAttribute(p, ids.getX(i + 2));
          expect(
            b.sub(a).cross(c.sub(a)).lengthSq(),
            `${definition.id}:${endpoint}`,
          ).toBeGreaterThan(1e-19);
        }
        disposeTemplateGarment(model);
      }
  });
  it("와이드 바지 JSON 계약·범위·종류 검증", () => {
    const input = resolveTemplateInput({
      category: "pants",
      template: "wide_pants",
      parameters: {
        waistWidth: 0.5,
        hipWidth: 0.6,
        thighWidth: 0.7,
        legLength: 0.8,
        hemWidth: 0.75,
      },
    });
    expect(input.template).toBe("slacks");
    expect(physicalParameters(input).hemWidth).toBeGreaterThan(0.25);
    expect(() =>
      resolveTemplateInput({ ...input, parameters: { rise: NaN } }),
    ).toThrow();
    expect(() =>
      resolveTemplateInput({ ...input, parameters: { rise: 1.01 } }),
    ).toThrow();
    expect(() => resolveTemplateInput({ ...input, category: "top" })).toThrow();
    expect(() =>
      resolveTemplateInput({ ...input, parameters: { constructor: 0.5 } }),
    ).toThrow();
  });
  it("마네킹 레이어 여유를 유지하고 셸 속은 비어 있다", () => {
    const top = createTemplateGarment(
      defaultTemplateInput("long_tshirt"),
      profile,
    );
    const outer = createTemplateGarment(
      defaultTemplateInput("jacket"),
      profile,
      top.envelope,
    );
    expect(outer.envelope.chest).toBeGreaterThan(top.envelope.chest + 0.02);
    expect(outer.envelope.sleeveRadius).toBeGreaterThan(
      top.envelope.sleeveRadius,
    );
    // 목에서 수직으로 본 몸통 내부에 뚜껑이 있어서는 안 된다.
    const ray = new Raycaster(new Vector3(0, 2, 0), new Vector3(0, -1, 0));
    top.group.updateMatrixWorld(true);
    expect(
      ray
        .intersectObject(top.group, true)
        .filter((hit) => hit.object instanceof Mesh),
    ).toHaveLength(0);
    const pants = createTemplateGarment(defaultTemplateInput("jeans"), profile);
    pants.group.updateMatrixWorld(true);
    const hip = physicalParameters(pants.input).hipWidth / 2;
    for (const sign of [-1, 1]) {
      const throughLeg = new Raycaster(
        new Vector3(sign * hip * 0.49, 1.4, 0),
        new Vector3(0, -1, 0),
      );
      expect(throughLeg.intersectObject(pants.group, true)).toHaveLength(0);
    }
    disposeTemplateGarment(pants);
    disposeTemplateGarment(top);
    disposeTemplateGarment(outer);
  });
});
