import { Suspense, useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { Box3 } from "three";
import type { Group } from "three";
import { getFittingResource } from "../../api/fittings";
import type {
  Adjustments,
  FittingResource,
  SlotSelection,
} from "../../types/fitting";
import type { Category } from "../../types/domain";
import { categories } from "../../types/domain";
import type { BodyProfile } from "../body/types";
import { bodyDimensions } from "../mannequin/geometry";
import { MannequinModel } from "../mannequin/MannequinModel";
import {
  CameraControls,
  ViewportBoundary,
} from "../mannequin/MannequinViewport";
import type { ViewCommand } from "../mannequin/MannequinViewport";
import { FittingModelCache, disposeScene } from "./fittingAssets";
import { fitGarment } from "./fitting";
import type { FitReport } from "./fitting";

const parts: Category[] = ["top", "bottom", "outer"];
interface Loaded {
  resource: FittingResource;
  scene: Group;
}
export default function FittingViewport({
  profile,
  token,
  selected,
  adjustments,
  pins,
  quality,
  reload,
}: {
  profile: BodyProfile;
  token?: string;
  selected: SlotSelection;
  adjustments: Adjustments;
  pins: Partial<Record<Category, string>>;
  quality: "light" | "standard";
  reload: number;
}) {
  const cache = useMemo(() => new FittingModelCache(), []);
  const [loaded, setLoaded] = useState<Partial<Record<Category, Loaded>>>({});
  const [errors, setErrors] = useState<Partial<Record<Category, string>>>({});
  const [command, setCommand] = useState<ViewCommand>({
    view: "front",
    sequence: 0,
  });
  const [ready, setReady] = useState(false);
  const selectedKey = JSON.stringify(selected),
    pinKey = JSON.stringify(pins);
  useEffect(() => () => cache.clear(), [cache]);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const selection: SlotSelection = JSON.parse(selectedKey);
    const expected: Partial<Record<Category, string>> = JSON.parse(pinKey);
    async function load() {
      const next: Partial<Record<Category, Loaded>> = {},
        failures: Partial<Record<Category, string>> = {};
      if (token) {
        const resources = await Promise.allSettled(
          parts.map(async (part) => {
            if (!selection[part]) return null;
            const resource = await getFittingResource(
              token!,
              selection[part]!,
              controller.signal,
            );
            if (resource.category !== part)
              throw new Error("모델 호환성 오류: 슬롯 카테고리가 다릅니다.");
            if (expected[part] && resource.model_asset_id !== expected[part])
              throw new Error(
                "저장 이후 모델이 변경되었습니다. 의류를 다시 선택해 주세요.",
              );
            return resource;
          }),
        );
        cache.setActive(
          resources.flatMap((result) =>
            result.status === "fulfilled" && result.value
              ? [result.value.model_asset_id]
              : [],
          ),
        );
        await Promise.all(
          resources.map(async (result, i) => {
            const part = parts[i];
            if (result.status === "rejected") {
              failures[part] =
                result.reason instanceof Error
                  ? result.reason.message
                  : "모델 접근에 실패했습니다.";
              return;
            }
            if (!result.value) return;
            try {
              next[part] = {
                resource: result.value,
                scene: await cache.load(
                  token!,
                  result.value,
                  controller.signal,
                ),
              };
            } catch (e) {
              failures[part] =
                `GLB 로딩 실패: ${e instanceof Error ? e.message : "다시 시도해 주세요."}`;
            }
          }),
        );
      } else
        for (const part of parts)
          if (selection[part])
            failures[part] = "로그인 후 본인 서버 모델을 선택해 주세요.";
      if (!controller.signal.aborted) {
        setErrors(failures);
        setLoaded((current) =>
          JSON.stringify(
            parts.map((p) => [
              current[p]?.resource.model_asset_id,
              current[p]?.resource.rights_version,
            ]),
          ) ===
          JSON.stringify(
            parts.map((p) => [
              next[p]?.resource.model_asset_id,
              next[p]?.resource.rights_version,
            ]),
          )
            ? current
            : next,
        );
        timer = setTimeout(() => void load(), 2000);
      }
    }
    void load();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [cache, token, selectedKey, pinKey, reload]);
  const fitted = useMemo(() => {
    const result: Partial<
        Record<Category, { group: Group; report: FitReport }>
      > = {},
      failures: Partial<Record<Category, string>> = {};
    for (const part of ["bottom", "top", "outer"] as const) {
      const entry = loaded[part];
      if (!entry || entry.resource.garment_id !== selected[part]) continue;
      try {
        result[part] = fitGarment(
          entry.scene,
          entry.resource,
          profile,
          adjustments[part],
          part === "top"
            ? [result.bottom?.group].filter((g): g is Group => !!g)
            : part === "outer"
              ? [result.top?.group, result.bottom?.group].filter(
                  (g): g is Group => !!g,
                )
              : [],
        );
      } catch (e) {
        failures[part] = e instanceof Error ? e.message : "모델 호환성 오류";
      }
    }
    return { models: result, failures };
  }, [loaded, profile, adjustments, selected]);
  useEffect(
    () => () => {
      for (const model of Object.values(fitted.models))
        disposeScene(model.group, true);
    },
    [fitted],
  );
  const reports = Object.values(fitted.models).map((m) => m.report);
  const bodyRemaining = reports.reduce(
    (n, r) => n + r.body_penetrations_after,
    0,
  );
  const layerRemaining = reports.reduce(
    (n, r) => n + r.layer_penetrations_after,
    0,
  );
  const d = bodyDimensions(profile);
  function send(view: ViewCommand["view"]) {
    setCommand((old) => ({ view, sequence: old.sequence + 1 }));
  }
  return (
    <section
      className="mannequin-viewport"
      aria-label="개인화 3D 피팅"
      data-body-revision={[
        d.values.height,
        d.values.shoulder,
        d.values.chest,
        d.values.waist,
        d.values.hip,
        d.values.arm,
        d.values.leg,
      ].join("/")}
      data-mounted-count={Object.keys(fitted.models).length}
      data-body-penetrations={bodyRemaining}
      data-body-before={reports.reduce(
        (n, r) => n + r.body_penetrations_before,
        0,
      )}
      data-layer-residual={layerRemaining}
      data-layer-before={reports.reduce(
        (n, r) => n + r.layer_penetrations_before,
        0,
      )}
      data-cache-entries={cache.stats.entries}
      data-cache-bytes={cache.stats.bytes}
      data-cache-hits={cache.stats.hits}
      data-fitted-bounds={JSON.stringify(
        Object.fromEntries(
          Object.entries(fitted.models).map(([part, model]) => {
            const box = new Box3().setFromObject(model.group);
            return [part, { min: box.min.toArray(), max: box.max.toArray() }];
          }),
        ),
      )}
    >
      <div className="viewport-heading">
        <span className="eyebrow">PERSONAL FITTING STUDIO</span>
        <span className="pill">시각적 근사 피팅</span>
      </div>
      <ViewportBoundary>
        <div
          className="canvas-wrap"
          role="img"
          aria-label="같은 3D 씬의 개인 마네킹과 실제 GLB 의류"
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
            <color attach="background" args={["#eee9f3"]} />
            <ambientLight intensity={1.5} />
            <directionalLight position={[3, 4, 5]} intensity={2.3} />
            <directionalLight position={[-3, 2, -3]} intensity={1.3} />
            <Suspense fallback={null}>
              <MannequinModel profile={profile} />
              {parts.map((part) =>
                fitted.models[part] ? (
                  <group
                    key={part}
                    visible={!adjustments[part].hidden}
                    name={`fitted_${part}`}
                  >
                    <primitive object={fitted.models[part]!.group} />
                  </group>
                ) : null,
              )}
            </Suspense>
            <CameraControls height={d.h} command={command} />
          </Canvas>
        </div>
      </ViewportBoundary>
      <div className="view-controls" role="group" aria-label="피팅 시점">
        {(
          [
            ["front", "정면"],
            ["side", "측면"],
            ["back", "후면"],
            ["zoom_in", "확대"],
            ["zoom_out", "축소"],
            ["reset", "초기화"],
          ] as const
        ).map(([view, label]) => (
          <button
            type="button"
            className="button secondary"
            key={view}
            disabled={!ready}
            onClick={() => send(view)}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="fitting-status" aria-live="polite">
        <p role="status">
          {ready ? "피팅 3D 준비 완료" : "피팅 3D 준비 중"} · 실제 의류{" "}
          {Object.keys(fitted.models).length}벌
        </p>
        {parts.map((part) =>
          selected[part] ? (
            <div key={part}>
              <p>
                {categories[part]}:{" "}
                {errors[part] ||
                  fitted.failures[part] ||
                  (fitted.models[part]
                    ? `${loaded[part]?.resource.reconstruction_mode}모드 · ${fitted.models[part]!.report.status === "insufficient" ? "치수 정보 부족 (추정치로 시각적 피팅)" : "시각적 피팅 가능"}${adjustments[part].hidden ? " · 숨김" : ""}`
                    : "GLB 불러오는 중…")}
              </p>
            </div>
          ) : null,
        )}
        <p>
          근사 관통 검사 잔여: 신체 {bodyRemaining}개 · 의류 {layerRemaining}개
          {bodyRemaining || layerRemaining
            ? " — 해결되지 않은 관통 가능성이 있습니다."
            : " — 표본 정점 검사 결과이며 모든 면의 교차가 없다는 보장은 아닙니다."}
        </p>
        <p className="helper">
          정밀 피팅 미지원. 실제 원단 움직임·압박·착용감은 계산하지 않습니다.
          숨김은 표시만 바꾸며 제거와 다릅니다.
        </p>
      </div>
    </section>
  );
}
