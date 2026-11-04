import { lazy, Suspense, useState } from "react";
import { useSession } from "../../stores/SessionContext";
import {
  defaultTemplateInput,
  physicalParameters,
  templateCatalog,
  templateDefinition,
} from "./catalog";
import type { TemplateCategory, TemplateId } from "./catalog";
import type { TemplateOutfit } from "./TemplateViewport";
import "./templates.css";

const TemplateViewport = lazy(() => import("./TemplateViewport"));
const initialOutfit = (): TemplateOutfit => ({
  top: defaultTemplateInput("short_tshirt"),
  pants: defaultTemplateInput("jeans"),
  outer: null,
});
const defaultIds: Record<TemplateCategory, TemplateId> = {
  top: "short_tshirt",
  pants: "jeans",
  outer: "zip_hoodie",
};
export default function TemplateWorkbench() {
  const { bodyProfiles, bodyMode } = useSession();
  const [outfit, setOutfit] = useState<TemplateOutfit>(initialOutfit);
  const [category, setCategory] = useState<TemplateCategory>("top");
  const [showParts, setShowParts] = useState(false),
    [quality, setQuality] = useState<"light" | "standard">("light");
  const current =
    outfit[category] ?? defaultTemplateInput(defaultIds[category]);
  const definition = templateDefinition(current.template),
    physical = physicalParameters(current);
  return (
    <section aria-label="6종 입체 의류 템플릿 편집기">
      <div className="template-intro">
        <div>
          <span className="eyebrow">GARMENT TEMPLATE LAB</span>
          <h2>내 마네킹에 맞춰 옷의 형태를 바꿔보세요</h2>
          <p>
            속이 빈 입체 의류 6종. 목·몸통·소매, 허리·엉덩이·바지통을 구분해
            변형합니다. 변경은 이 화면의 메모리에만 유지됩니다.
          </p>
        </div>
        <a className="button secondary" href="#/body">
          마네킹 체형 변경
        </a>
      </div>
      <div className="template-workspace">
        <div className="template-controls panel">
          <label className="field">
            의류 종류
            <select
              aria-label="의류 종류"
              value={category}
              onChange={(e) => setCategory(e.target.value as TemplateCategory)}
            >
              <option value="top">상의</option>
              <option value="pants">하의</option>
              <option value="outer">외투</option>
            </select>
          </label>
          <label className="field">
            의류 템플릿
            <select
              aria-label="의류 템플릿"
              value={current.template}
              onChange={(e) =>
                setOutfit((old) => ({
                  ...old,
                  [category]: defaultTemplateInput(
                    e.target.value as TemplateId,
                  ),
                }))
              }
            >
              {templateCatalog
                .filter((item) => item.category === category)
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
            </select>
          </label>
          <div className="action-row">
            <button
              type="button"
              className="button primary"
              onClick={() =>
                setOutfit((old) => ({
                  ...old,
                  [category]: outfit[category] ? null : current,
                }))
              }
            >
              {outfit[category] ? "선택 의류 제거" : "선택 의류 입히기"}
            </button>
            <button
              type="button"
              className="button secondary"
              disabled={!outfit[category]}
              onClick={() =>
                setOutfit((old) => ({
                  ...old,
                  [category]: defaultTemplateInput(current.template),
                }))
              }
            >
              형태 초기화
            </button>
          </div>
          <h3>{definition.name} 형태</h3>
          <p className="helper">
            0~1의 디자인 값을 길이·폭 범위에 연결합니다. 표시한 cm는 디자인
            기준이며 체형과 안쪽 의류의 여유에 따라 보정될 수 있습니다.
          </p>
          {definition.parameters.map((p) => (
            <label className="template-slider" key={p.key}>
              <span>
                {p.label}
                <output>
                  {current.parameters[p.key].toFixed(2)} ·{" "}
                  {(physical[p.key] * 100).toFixed(1)} cm 기준
                </output>
              </span>
              <input
                aria-label={`${p.label} 조절`}
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={current.parameters[p.key]}
                disabled={!outfit[category]}
                onChange={(e) => {
                  const value = Number(e.target.value);
                  setOutfit((old) => ({
                    ...old,
                    [category]: {
                      ...current,
                      parameters: { ...current.parameters, [p.key]: value },
                    },
                  }));
                }}
              />
            </label>
          ))}
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={showParts}
              onChange={(e) => setShowParts(e.target.checked)}
            />
            부위별 색상으로 보기
          </label>
          <label className="field">
            렌더링 품질
            <select
              aria-label="렌더링 품질"
              value={quality}
              onChange={(e) => setQuality(e.target.value as typeof quality)}
            >
              <option value="light">모바일 경량</option>
              <option value="standard">표준</option>
            </select>
          </label>
          <div className="action-row">
            <button
              type="button"
              className="button secondary"
              onClick={() => setOutfit({ top: null, pants: null, outer: null })}
            >
              의류 모두 제거
            </button>
            <button
              type="button"
              className="button secondary"
              onClick={() => setOutfit(initialOutfit())}
            >
              전체 의류 초기화
            </button>
          </div>
        </div>
        <Suspense fallback={<p role="status">의류 템플릿 준비 중…</p>}>
          <TemplateViewport
            profile={bodyProfiles[bodyMode]}
            outfit={outfit}
            showParts={showParts}
            quality={quality}
          />
        </Suspense>
      </div>
    </section>
  );
}
