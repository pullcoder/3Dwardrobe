import { useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import type { BodyProfile } from "../body/types";
import { MannequinModel } from "../mannequin/MannequinModel";
import {
  CameraControls,
  ViewportBoundary,
} from "../mannequin/MannequinViewport";
import type { ViewCommand } from "../mannequin/MannequinViewport";
import { bodyDimensions } from "../mannequin/geometry";
import {
  createTemplateGarment,
  disposeTemplateGarment,
} from "./garmentGeometry";
import type { TemplateMesh } from "./garmentGeometry";
import type { ResolvedTemplateInput, TemplateCategory } from "./catalog";

export type TemplateOutfit = Record<
  TemplateCategory,
  ResolvedTemplateInput | null
>;
function useCleanup(model: TemplateMesh | null) {
  useEffect(
    () => () => {
      if (model) disposeTemplateGarment(model);
    },
    [model],
  );
}
export default function TemplateViewport({
  profile,
  outfit,
  showParts,
  quality,
}: {
  profile: BodyProfile;
  outfit: TemplateOutfit;
  showParts: boolean;
  quality: "light" | "standard";
}) {
  const [command, setCommand] = useState<ViewCommand>({
    view: "front",
    sequence: 0,
  });
  const [ready, setReady] = useState(false);
  const bottom = useMemo(
    () =>
      outfit.pants
        ? createTemplateGarment(outfit.pants, profile, undefined, showParts)
        : null,
    [outfit.pants, profile, showParts],
  );
  const top = useMemo(
    () =>
      outfit.top
        ? createTemplateGarment(
            outfit.top,
            profile,
            bottom?.envelope,
            showParts,
          )
        : null,
    [outfit.top, profile, bottom, showParts],
  );
  const outer = useMemo(
    () =>
      outfit.outer
        ? createTemplateGarment(
            outfit.outer,
            profile,
            top?.envelope ?? bottom?.envelope,
            showParts,
          )
        : null,
    [outfit.outer, profile, top, bottom, showParts],
  );
  useCleanup(bottom);
  useCleanup(top);
  useCleanup(outer);
  const models = [bottom, top, outer].filter((m): m is TemplateMesh => !!m);
  const d = bodyDimensions(profile);
  const signature = models
    .map((model) => {
      const p = model.geometry.getAttribute("position");
      let value = 0;
      for (let i = 0; i < p.count; i++)
        value +=
          p.getX(i) * ((i % 13) + 1) +
          p.getY(i) * ((i % 7) + 1) +
          p.getZ(i) * ((i % 5) + 1);
      return `${model.input.template}:${value.toFixed(5)}`;
    })
    .join("/");
  return (
    <section
      className="mannequin-viewport template-viewport"
      aria-label="의류 템플릿 착용 결과"
      data-mounted-count={models.length}
      data-shape-signature={signature}
      data-triangles={models.reduce((n, m) => n + m.stats.triangles, 0)}
      data-templates={models.map((m) => m.input.template).join(",")}
    >
      <div className="viewport-heading">
        <span className="eyebrow">LIVE GARMENT DESIGN</span>
        <span className="pill">입체 의류 · {models.length}벌</span>
      </div>
      <ViewportBoundary>
        <div
          className="canvas-wrap"
          role="img"
          aria-label="기존 마네킹과 속이 빈 입체 의류 템플릿"
        >
          <Canvas
            key={quality}
            frameloop="demand"
            dpr={quality === "light" ? 1 : [1, 1.5]}
            camera={{ position: [0, 1, 3.2], fov: 38 }}
            gl={{
              antialias: quality === "standard",
              preserveDrawingBuffer: true,
            }}
            onCreated={() => setReady(true)}
            fallback={
              <p role="alert">WebGL을 지원하는 브라우저가 필요합니다.</p>
            }
          >
            <color attach="background" args={["#edf0f2"]} />
            <ambientLight intensity={0.65} />
            <hemisphereLight args={["#ffffff", "#72747a", 0.65]} />
            <directionalLight position={[-3, 4, 5]} intensity={2} />
            <directionalLight position={[3, 2, -3]} intensity={1} />
            <MannequinModel profile={profile} />
            {models.map((model) => (
              <primitive
                key={model.input.category}
                object={model.group}
                dispose={null}
              />
            ))}
            <CameraControls height={d.h} command={command} />
          </Canvas>
        </div>
      </ViewportBoundary>
      <div className="view-controls" role="group" aria-label="템플릿 시점">
        {(
          [
            ["front", "정면"],
            ["side", "측면"],
            ["back", "후면"],
            ["zoom_in", "확대"],
            ["zoom_out", "축소"],
            ["reset", "시점 초기화"],
          ] as const
        ).map(([view, label]) => (
          <button
            key={view}
            type="button"
            className="button secondary"
            disabled={!ready}
            onClick={() =>
              setCommand((old) => ({ view, sequence: old.sequence + 1 }))
            }
          >
            {label}
          </button>
        ))}
      </div>
      <p role="status">
        {ready ? "템플릿 3D 준비 완료" : "3D 준비 중…"} · {models.length}벌
      </p>
      <p className="helper">
        드래그로 360° 회전 · 휠/핀치로 확대. 몸통·팔·다리의 근사 공간과 레이어
        여유를 반영합니다. 정밀 충돌 해결·원단 물리·실제 착용감은 계산하지
        않습니다.
      </p>
      <details>
        <summary>의류 메시 구조</summary>
        <ul>
          {models.map((m) => (
            <li key={m.input.template}>
              {m.input.template} · {m.stats.triangles.toLocaleString()}면 ·
              개구부 테두리 {m.stats.openings}개 · 부위 {m.stats.parts.length}개
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}
