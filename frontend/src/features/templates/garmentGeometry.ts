// 부위별 로프트와 연결된 암홀/가랑이. 박스·사진 평면을 의류로 사용하지 않는다.
import {
  BufferGeometry,
  Float32BufferAttribute,
  Group,
  Mesh,
  MeshStandardMaterial,
  Vector3,
} from "three";
import type { BodyProfile } from "../body/types";
import { bodyDimensions, ellipseRadius } from "../mannequin/geometry";
import {
  physicalParameters,
  resolveTemplateInput,
  templateDefinition,
} from "./catalog";
import type { ResolvedTemplateInput, TemplateCategory } from "./catalog";

type Point = [number, number, number];
export const semanticParts = [
  "body",
  "collar",
  "sleeve_left",
  "sleeve_right",
  "waist",
  "hips",
  "leg_left",
  "leg_right",
  "hood",
  "edge_binding",
] as const;
const partIndex = (name: (typeof semanticParts)[number]) =>
  semanticParts.indexOf(name);
interface Surface {
  points: Point[];
  uv: number[][];
  faces: number[][];
  parts: number[];
}
export interface GarmentEnvelope {
  category: TemplateCategory;
  chest: number;
  depth: number;
  shoulder: number;
  sleeveRadius: number;
  length: number;
}
export interface TemplateMesh {
  input: ResolvedTemplateInput;
  group: Group;
  geometry: BufferGeometry;
  envelope: GarmentEnvelope;
  stats: {
    triangles: number;
    vertices: number;
    correctedVertices: number;
    openings: number;
    parts: string[];
    topologyReused: boolean;
  };
}
const N = 48;
const topologyCache = new Map<string, number[]>();
const clamp = (v: number, lo: number, hi: number) =>
  Math.max(lo, Math.min(hi, v));
const mix = (a: number, b: number, t: number) => a + (b - a) * t;
function vertex(s: Surface, p: Point, uv: number[]) {
  s.points.push(p);
  s.uv.push(uv);
  return s.points.length - 1;
}
function face(
  s: Surface,
  a: number,
  b: number,
  c: number,
  part: number,
  normal: Point,
) {
  const pa = new Vector3(...s.points[a]),
    pb = new Vector3(...s.points[b]),
    pc = new Vector3(...s.points[c]);
  const cross = pb.sub(pa).cross(pc.sub(pa));
  if (cross.dot(new Vector3(...normal)) < 0) [b, c] = [c, b];
  s.faces.push([a, b, c]);
  s.parts.push(part);
}
function quad(
  s: Surface,
  a: number,
  b: number,
  c: number,
  d: number,
  part: number,
  normal: Point,
) {
  face(s, a, b, c, part, normal);
  face(s, c, b, d, part, normal);
}
function capsule(p: Point, a: Point, b: Point, radius: number) {
  const axis = new Vector3(...b).sub(new Vector3(...a));
  const relative = new Vector3(...p).sub(new Vector3(...a));
  const nearest = new Vector3(...a).addScaledVector(
    axis,
    clamp(relative.dot(axis) / axis.lengthSq(), 0, 1),
  );
  const delta = new Vector3(...p).sub(nearest),
    length = delta.length();
  if (length >= radius) return false;
  if (length < 1e-8) delta.set(p[0] >= 0 ? 1 : -1, 0, 0);
  delta.normalize().multiplyScalar(radius).add(nearest);
  p[0] = delta.x;
  p[1] = delta.y;
  p[2] = delta.z;
  return true;
}
function bodyGuard(
  s: Surface,
  profile: BodyProfile,
  category: string,
  margin: number,
) {
  const d = bodyDimensions(profile),
    hip = ellipseRadius(d.values.hip);
  const rings = [
    [d.hip - d.h * 0.055, hip * 0.72],
    [d.hip, hip],
    [d.waist, ellipseRadius(d.values.waist)],
    [d.chest, ellipseRadius(d.values.chest)],
    [d.shoulder - d.h * 0.025, d.width * 0.46],
    [d.shoulder + d.h * 0.005, d.width * 0.3],
  ];
  let corrected = 0;
  for (const p of s.points) {
    let changed = false;
    if (p[1] >= rings[0][0] && p[1] <= rings.at(-1)![0]) {
      const i = Math.max(
        1,
        rings.findIndex((r) => r[0] >= p[1]),
      );
      const t = (p[1] - rings[i - 1][0]) / (rings[i][0] - rings[i - 1][0]);
      const rx = mix(rings[i - 1][1], rings[i][1], t) + margin,
        rz = (rx - margin) * 0.72 + margin;
      const ratio = Math.hypot(p[0] / rx, p[2] / rz);
      if (ratio > 1e-8 && ratio < 1) {
        p[0] /= ratio;
        p[2] /= ratio;
        changed = true;
      }
    }
    // 기존 마네킹과 같은 사지 축을 사용한다.
    for (const sign of [-1, 1]) {
      if (category !== "pants") {
        const shoulder: Point = [(sign * d.width) / 2, d.shoulder, 0];
        const elbow: Point = [
          sign * (d.width / 2 + d.arm * 0.11),
          d.shoulder - d.arm * 0.5,
          0,
        ];
        const wrist: Point = [
          sign * (d.width / 2 + d.arm * 0.19),
          d.shoulder - d.arm * 0.98,
          0.015,
        ];
        const shoulderEase = p[1] > d.shoulder - 0.2 ? 0.012 : 0;
        changed =
          capsule(p, shoulder, elbow, d.h * 0.023 + margin + shoulderEase) ||
          changed;
        changed = capsule(p, elbow, wrist, d.h * 0.019 + margin) || changed;
      } else {
        const start: Point = [sign * hip * 0.47, d.hip, 0];
        const knee: Point = [sign * hip * 0.49, (d.hip + d.ankle) * 0.5, 0.007];
        const ankle: Point = [sign * hip * 0.5, d.ankle, 0];
        changed = capsule(p, start, knee, hip * 0.4 + margin) || changed;
        changed = capsule(p, knee, ankle, d.h * 0.03 + margin) || changed;
      }
    }
    if (changed) corrected++;
  }
  return corrected;
}

function upperSurface(
  s: Surface,
  input: ResolvedTemplateInput,
  profile: BodyProfile,
  inner?: GarmentEnvelope,
) {
  const p = physicalParameters(input),
    d = bodyDimensions(profile),
    outer = input.category === "outer";
  const lowerUnderTop = !outer && inner?.category === "pants";
  const chest = Math.max(
    p.chestWidth ?? p.bodyWidth,
    (inner?.chest ?? 0) / (lowerUnderTop ? 0.94 : 1) +
      (outer ? 0.028 : lowerUnderTop ? 0.014 : 0),
  );
  const shoulder = Math.max(
    p.shoulderWidth,
    (inner?.shoulder ?? 0) + (outer ? 0.018 : 0),
  );
  const length = p.length,
    topY = d.shoulder + 0.018,
    bottom = topY - length;
  const depth = Math.max(
    chest * 0.72,
    (inner?.depth ?? 0) + (outer ? 0.026 : lowerUnderTop ? 0.014 : 0),
  );
  const ys = [
    ...Array.from({ length: 10 }, (_, i) => mix(bottom, topY - 0.24, i / 9)),
    ...[0.2, 0.16, 0.12, 0.085, 0.05, 0.025, 0.008, -0.008].map(
      (v) => topY - v,
    ),
  ];
  const rings: number[][] = [];
  for (let r = 0; r < ys.length; r++) {
    const y =
        r === 15 ? d.shoulder + 0.05 : r === 16 ? d.shoulder + 0.045 : ys[r],
      t = (y - bottom) / length;
    const width =
      r === 17
        ? 0.15
        : r === 16
          ? shoulder * 0.62
          : r === 15
            ? shoulder
            : chest * (0.94 + 0.06 * Math.sin(Math.PI * t));
    const zWidth = r === 17 ? 0.13 : r === 16 ? depth * 0.5 : depth;
    rings.push(
      Array.from({ length: N }, (_, j) => {
        const a = (j / N) * Math.PI * 2;
        const py =
          r === 15
            ? d.shoulder + 0.008 + 0.04 * Math.cos(a) ** 2
            : r === 16
              ? d.shoulder + 0.018 + 0.027 * Math.cos(a) ** 2
              : r === 17
                ? y - 0.023 * Math.max(0, Math.sin(a))
                : y;
        const ripple =
          0.0015 * Math.sin(a * 8 + y * 9) * Math.sin(Math.PI * clamp(t, 0, 1));
        return vertex(
          s,
          [
            (width / 2 + ripple) * Math.cos(a),
            py,
            (zWidth / 2 + ripple) * Math.sin(a),
          ],
          [j / N, clamp(1 - t, 0, 1)],
        );
      }),
    );
  }
  const lo = 9,
    hi = 14,
    half = 4;
  const inHole = (j: number, center: number) => {
    const v = ((j - center + N + N / 2) % N) - N / 2;
    return v >= -half && v < half;
  };
  for (let r = 0; r < rings.length - 1; r++)
    for (let j = 0; j < N; j++) {
      if (r >= lo && r < hi && (inHole(j, 0) || inHole(j, N / 2))) continue;
      if (outer && (j === N / 4 - 1 || j === N / 4)) continue;
      const k = (j + 1) % N,
        a = (j / N) * Math.PI * 2;
      quad(
        s,
        rings[r][j],
        rings[r + 1][j],
        rings[r][k],
        rings[r + 1][k],
        partIndex(r >= 15 ? "collar" : "body"),
        [Math.cos(a), 0.2, Math.sin(a)],
      );
    }
  const sleeveRadius = Math.max(
    outer ? 0.075 : 0.067,
    (inner?.sleeveRadius ?? 0) + (outer ? 0.009 : 0),
  );
  for (const [center, sign] of [
    [0, 1],
    [N / 2, -1],
  ]) {
    const at = (r: number, j: number) => rings[r][(j + N) % N];
    const loop: number[] = [];
    for (let j = center - half; j <= center + half; j++) loop.push(at(lo, j));
    for (let r = lo + 1; r <= hi; r++) loop.push(at(r, center + half));
    for (let j = center + half - 1; j >= center - half; j--)
      loop.push(at(hi, j));
    for (let r = hi - 1; r > lo; r--) loop.push(at(r, center - half));
    const holeCenter = loop
      .reduce((v, id) => v.add(new Vector3(...s.points[id])), new Vector3())
      .divideScalar(loop.length);
    const startAngle = Math.atan2(
      s.points[loop[0]][2],
      s.points[loop[0]][1] - holeCenter.y,
    );
    let area = 0;
    loop.forEach((id, i) => {
      const a = s.points[id],
        b = s.points[loop[(i + 1) % loop.length]];
      area += (a[1] - holeCenter.y) * b[2] - (b[1] - holeCenter.y) * a[2];
    });
    let previous = loop;
    for (let row = 1; row <= 10; row++) {
      const t = row / 10,
        blend = Math.min(1, t * 3),
        desiredY = topY - p.sleeveLength;
      const cy = mix(holeCenter.y, desiredY, t),
        cx = mix(
          holeCenter.x,
          sign * (shoulder / 2 + p.sleeveLength * 0.19),
          t,
        );
      const radius = mix(
        sleeveRadius,
        p.sleeveLength < 0.36 ? sleeveRadius * 0.95 : sleeveRadius * 0.74,
        t,
      );
      const next = loop.map((id, j) => {
        const a =
          startAngle + ((Math.sign(area) * j) / loop.length) * Math.PI * 2;
        const old = s.points[id];
        const x =
          cx +
          mix(
            old[0] - holeCenter.x,
            sign * 0.985 * Math.cos(a) * radius,
            blend,
          );
        const y =
          cy + mix(old[1] - holeCenter.y, 0.17 * Math.cos(a) * radius, blend);
        const z = mix(old[2], Math.sin(a) * radius * 0.9, blend);
        return vertex(s, [x, y, z], [j / loop.length, t]);
      });
      next.forEach((id, j) => {
        const k = (j + 1) % next.length,
          pt = s.points[id];
        quad(
          s,
          previous[j],
          id,
          previous[k],
          next[k],
          partIndex(sign > 0 ? "sleeve_left" : "sleeve_right"),
          [pt[0] - cx, 0, pt[2]],
        );
      });
      previous = next;
    }
  }
  if (input.template === "zip_hoodie") hoodSurface(s, profile);
  return {
    category: input.category,
    chest,
    depth,
    shoulder,
    sleeveRadius,
    length,
  };
}

function hoodSurface(s: Surface, profile: BodyProfile) {
  const d = bodyDimensions(profile),
    rows: number[][] = [];
  for (let r = 0; r < 12; r++) {
    const phi = mix(-1.05, 1.4, r / 11);
    rows.push(
      Array.from({ length: 29 }, (_, j) => {
        const a = mix(0.28, -Math.PI - 0.28, j / 28);
        return vertex(
          s,
          [
            0.125 * Math.cos(phi) * Math.cos(a),
            d.h * 0.925 + 0.18 * Math.sin(phi),
            0.015 + 0.14 * Math.cos(phi) * Math.sin(a),
          ],
          [j / 28, r / 12],
        );
      }),
    );
  }
  for (let r = 0; r < rows.length - 1; r++)
    for (let j = 0; j < 28; j++) {
      const p = s.points[rows[r][j]];
      quad(
        s,
        rows[r][j],
        rows[r + 1][j],
        rows[r][j + 1],
        rows[r + 1][j + 1],
        partIndex("hood"),
        [p[0], p[1] - d.h * 0.925, p[2] - 0.015],
      );
    }
  const crown = vertex(s, [0, d.h * 0.925 + 0.18, 0.015], [0.5, 1]);
  for (let j = 0; j < 28; j++)
    face(
      s,
      rows.at(-1)![j],
      crown,
      rows.at(-1)![j + 1],
      partIndex("hood"),
      [0, 1, 0],
    );
}

function pantsSurface(
  s: Surface,
  input: ResolvedTemplateInput,
  profile: BodyProfile,
) {
  const p = physicalParameters(input),
    d = bodyDimensions(profile);
  const waistY = d.waist,
    hemY = Math.max(0.025, waistY - p.legLength),
    crotchY = waistY - p.rise;
  const waist = p.waistWidth / 2,
    hip = p.hipWidth / 2,
    rz = hip * 0.78,
    rows: number[][] = [];
  for (let r = 0; r < 9; r++) {
    const t = r / 8,
      rx = mix(waist, hip, Math.sin((t * Math.PI) / 2));
    rows.push(
      Array.from({ length: N }, (_, j) => {
        const a = (j / N) * Math.PI * 2;
        return vertex(
          s,
          [rx * Math.cos(a), mix(waistY, crotchY, t), rx * 0.78 * Math.sin(a)],
          [j / N, t * 0.35],
        );
      }),
    );
  }
  for (let r = 0; r < 8; r++)
    for (let j = 0; j < N; j++) {
      const k = (j + 1) % N,
        a = (j / N) * Math.PI * 2;
      quad(
        s,
        rows[r][j],
        rows[r + 1][j],
        rows[r][k],
        rows[r + 1][k],
        partIndex(r < 2 ? "waist" : "hips"),
        [Math.cos(a), 0, Math.sin(a)],
      );
    }
  const bridge: number[] = [];
  for (let j = 1; j < 12; j++) {
    const z = mix(-rz, rz, j / 12);
    bridge.push(
      vertex(
        s,
        [0, crotchY + 0.035 * Math.sin((j / 12) * Math.PI), z],
        [0.5, j / 12],
      ),
    );
  }
  for (const sign of [-1, 1]) {
    const start = sign < 0 ? N / 4 : (N * 3) / 4;
    const outside = Array.from(
      { length: N / 2 + 1 },
      (_, j) => rows[8][(start + j) % N],
    );
    const loop = [...outside, ...(sign < 0 ? bridge : [...bridge].reverse())];
    let previous = loop;
    for (let r = 1; r <= 16; r++) {
      const t = r / 16,
        cy = mix(crotchY, hemY, t),
        cx = sign * hip * 0.49;
      const rx = mix(p.thighWidth / 2, p.hemWidth / 2, Math.pow(t, 0.8));
      const next = loop.map((id, j) => {
        const a =
          j <= 24
            ? mix(
                sign < 0 ? Math.PI / 2 : -Math.PI / 2,
                sign < 0 ? Math.PI * 1.5 : Math.PI / 2,
                j / 24,
              )
            : mix(
                sign < 0 ? Math.PI * 1.5 : Math.PI / 2,
                sign < 0 ? Math.PI * 2.5 : Math.PI * 1.5,
                (j - 24) / 12,
              );
        const blend = Math.min(1, t * 4),
          old = s.points[id];
        const targetX =
          sign * Math.max(0.004, Math.abs(cx) + sign * rx * Math.cos(a));
        return vertex(
          s,
          [
            mix(old[0], targetX, blend),
            cy + (old[1] - crotchY) * (1 - blend),
            mix(old[2], rx * 0.85 * Math.sin(a), blend),
          ],
          [j / loop.length, 0.35 + t * 0.65],
        );
      });
      next.forEach((id, j) => {
        const k = (j + 1) % loop.length,
          pt = s.points[id];
        quad(
          s,
          previous[j],
          id,
          previous[k],
          next[k],
          partIndex(sign < 0 ? "leg_left" : "leg_right"),
          [pt[0] - cx, 0, pt[2]],
        );
      });
      previous = next;
    }
  }
  return {
    category: input.category,
    chest: Math.max(p.hipWidth, p.hipWidth * 0.49 + p.thighWidth),
    depth: p.hipWidth * 0.78,
    shoulder: 0,
    sleeveRadius: 0,
    length: waistY - hemY,
  };
}

function edges(s: Surface) {
  const found = new Map<string, { a: number; b: number; count: number }>();
  for (const tri of s.faces)
    for (let i = 0; i < 3; i++) {
      const a = tri[i],
        b = tri[(i + 1) % 3],
        key = a < b ? `${a}/${b}` : `${b}/${a}`;
      const old = found.get(key);
      if (old) old.count++;
      else found.set(key, { a, b, count: 1 });
    }
  if ([...found.values()].some((e) => e.count > 2))
    throw new Error("의류 연결에 비정상 분기 면이 있습니다.");
  return [...found.values()].filter((e) => e.count === 1);
}
function orientSurface(s: Surface) {
  // 연결 부위와 어깨의 기울기가 바뀌어도 공유 간선의 방향은 항상 반대여야 한다.
  const uses = new Map<string, { face: number; direction: number }[]>();
  s.faces.forEach((tri, index) => {
    for (let j = 0; j < 3; j++) {
      const a = tri[j],
        b = tri[(j + 1) % 3],
        key = a < b ? `${a}/${b}` : `${b}/${a}`;
      uses.set(key, [
        ...(uses.get(key) ?? []),
        { face: index, direction: a < b ? 1 : -1 },
      ]);
    }
  });
  const adjacent: { face: number; factor: number }[][] = s.faces.map(() => []);
  for (const list of uses.values()) {
    if (list.length > 2) throw new Error("의류 면이 비정상적으로 분기합니다.");
    if (list.length === 2) {
      const [a, b] = list,
        factor = -a.direction * b.direction;
      adjacent[a.face].push({ face: b.face, factor });
      adjacent[b.face].push({ face: a.face, factor });
    }
  }
  const directions = new Int8Array(s.faces.length);
  for (let seed = 0; seed < s.faces.length; seed++) {
    if (directions[seed]) continue;
    directions[seed] = 1;
    const pending = [seed];
    while (pending.length) {
      const current = pending.pop()!;
      for (const other of adjacent[current]) {
        const wanted = directions[current] * other.factor;
        if (directions[other.face] && directions[other.face] !== wanted)
          throw new Error("의류의 안팎 방향을 일관되게 연결할 수 없습니다.");
        if (!directions[other.face]) {
          directions[other.face] = wanted;
          pending.push(other.face);
        }
      }
    }
  }
  s.faces.forEach((tri, index) => {
    if (directions[index] < 0) [tri[1], tri[2]] = [tri[2], tri[1]];
  });
}
function thicken(s: Surface) {
  const boundary = edges(s),
    count = s.points.length;
  const remaining = new Set(boundary.flatMap(({ a, b }) => [a, b]));
  const graph = new Map<number, number[]>();
  for (const { a, b } of boundary) {
    graph.set(a, [...(graph.get(a) ?? []), b]);
    graph.set(b, [...(graph.get(b) ?? []), a]);
  }
  let loops = 0;
  while (remaining.size) {
    const pending = [remaining.values().next().value!];
    loops++;
    while (pending.length) {
      const id = pending.pop()!;
      if (!remaining.delete(id)) continue;
      pending.push(
        ...(graph.get(id) ?? []).filter((other) => remaining.has(other)),
      );
    }
  }
  const source = new BufferGeometry();
  source.setAttribute(
    "position",
    new Float32BufferAttribute(s.points.flat(), 3),
  );
  source.setIndex(s.faces.flat());
  source.computeVertexNormals();
  const normals = source.getAttribute("normal");
  for (let i = 0; i < count; i++) {
    const p = s.points[i];
    vertex(
      s,
      [
        p[0] - normals.getX(i) * 0.0018,
        p[1] - normals.getY(i) * 0.0018,
        p[2] - normals.getZ(i) * 0.0018,
      ],
      s.uv[i],
    );
  }
  const faces = [...s.faces],
    parts = [...s.parts];
  faces.forEach(([a, b, c], i) => {
    s.faces.push([a + count, c + count, b + count]);
    s.parts.push(parts[i]);
  });
  for (const { a, b } of boundary) {
    s.faces.push([a, a + count, b], [b, a + count, b + count]);
    s.parts.push(partIndex("edge_binding"), partIndex("edge_binding"));
  }
  source.dispose();
  // 정상 의류 개구부의 테두리를 연결해 두께를 주며 공간 자체를 막지 않는다.
  return loops;
}

export function createTemplateGarment(
  value: unknown,
  profile: BodyProfile,
  inner?: GarmentEnvelope,
  showParts = false,
): TemplateMesh {
  const input = resolveTemplateInput(value),
    definition = templateDefinition(input.template);
  const surface: Surface = { points: [], uv: [], faces: [], parts: [] };
  const envelope =
    input.category === "pants"
      ? pantsSurface(surface, input, profile)
      : upperSurface(surface, input, profile, inner);
  const correctedVertices = bodyGuard(
    surface,
    profile,
    input.category,
    input.category === "outer" ? 0.014 : 0.007,
  );
  orientSurface(surface);
  const openings = thicken(surface);
  const positions = new Float32BufferAttribute(surface.points.flat(), 3),
    uv = new Float32BufferAttribute(surface.uv.flat(), 2);
  const indices: number[] = [],
    groups: { start: number; count: number; materialIndex: number }[] = [];
  const used: string[] = [];
  semanticParts.forEach((name, part) => {
    const start = indices.length;
    surface.faces.forEach((f, i) => {
      if (surface.parts[i] === part) indices.push(...f);
    });
    if (indices.length > start) {
      groups.push({
        start,
        count: indices.length - start,
        materialIndex: part,
      });
      used.push(name);
    }
  });
  const cached = topologyCache.get(input.template),
    topologyReused = !!cached;
  if (!cached) topologyCache.set(input.template, indices);
  else if (cached.length !== indices.length)
    throw new Error("의류 템플릿의 연결 구조가 변경되었습니다.");
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", positions);
  geometry.setAttribute("uv", uv);
  geometry.setIndex(cached ?? indices);
  groups.forEach((g) => geometry.addGroup(g.start, g.count, g.materialIndex));
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  geometry.userData = {
    semantic_parts: semanticParts,
    unit: "meter",
    coordinate_system: "y_up_z_front",
    thickness_m: 0.0018,
  };
  const palette = [
    "#619bb0",
    "#e8c477",
    "#c78487",
    "#85ab86",
    "#d4bb87",
    "#7f9cba",
    "#c28e91",
    "#82aa9e",
    "#b49bc1",
    "#d6cfbd",
  ];
  const materials = semanticParts.map(
    (name, i) =>
      new MeshStandardMaterial({
        name,
        color: showParts ? palette[i] : definition.color,
        roughness: input.template === "jeans" ? 0.94 : 0.84,
        metalness: 0,
      }),
  );
  const mesh = new Mesh(geometry, materials);
  mesh.name = input.template;
  const group = new Group();
  group.name = `template_${input.template}`;
  group.add(mesh);
  const stats = {
    triangles: indices.length / 3,
    vertices: positions.count,
    correctedVertices,
    openings,
    parts: used,
    topologyReused,
  };
  group.userData = {
    template: input.template,
    category: input.category,
    parameters: input.parameters,
    stats,
    generation_kind: "project_original_template",
  };
  return { input, group, geometry, envelope, stats };
}
export function disposeTemplateGarment(model: TemplateMesh) {
  model.geometry.dispose();
  model.group.traverse((object) => {
    if (object instanceof Mesh)
      for (const material of Array.isArray(object.material)
        ? object.material
        : [object.material])
        material.dispose();
  });
}
