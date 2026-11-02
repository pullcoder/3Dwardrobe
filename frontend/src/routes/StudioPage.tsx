import { lazy, Suspense, useState } from "react";
import { Box, Layers, Plus } from "lucide-react";
import {
  ComingButton,
  LinkButton,
  Notice,
  PageHeading,
} from "../components/UI";
import { useSession } from "../stores/SessionContext";
import { categories } from "../types/domain";
import type { Category } from "../types/domain";
import "../features/body/body.css";

const MannequinViewport = lazy(
  () => import("../features/mannequin/MannequinViewport"),
);

export function StudioPage() {
  const { garments, bodyProfiles, bodyMode } = useSession();
  const [selected, setSelected] = useState<Partial<Record<Category, string>>>(
    {},
  );
  return (
    <>
      <PageHeading
        eyebrow="YOUR FITTING SPACE"
        title="3D 피팅 스튜디오"
        description="상의, 하의, 겉옷을 조합할 나만의 공간."
      />
      <Notice>
        현재 선택한 체형의 3D 마네킹을 표시합니다. 아래 의류 선택은 슬롯 UI만
        변경합니다. 의류를 입히거나 3D·물리 피팅 결과를 만들지 않습니다 (5단계
        예정).
      </Notice>
      <div className="studio-layout">
        <section className="studio-canvas">
          <div className="studio-top">
            <span>
              <Box size={17} /> STUDIO / PREVIEW
            </span>
            <span className="pill">
              {bodyMode === "photo" ? "사진 분석 체형" : "수동 입력 체형"}
            </span>
          </div>
          <Suspense fallback={<p role="status">3D 뷰어 준비 중…</p>}>
            <MannequinViewport profile={bodyProfiles[bodyMode]} />
          </Suspense>
        </section>
        <aside className="panel slot-panel">
          <div className="panel-heading">
            <h2>
              <Layers size={20} />
              의류 슬롯 준비
            </h2>
            <p>상의 위에 겉옷을 더하는 세 가지 슬롯.</p>
          </div>
          {(Object.entries(categories) as [Category, string][]).map(
            ([key, label]) => (
              <div className="slot" key={key}>
                <label htmlFor={`slot-${key}`}>
                  {label}
                  <span>
                    {key === "outer"
                      ? "LAYER 03"
                      : key === "top"
                        ? "LAYER 02"
                        : "LAYER 01"}
                  </span>
                </label>
                <select
                  id={`slot-${key}`}
                  value={selected[key] || ""}
                  onChange={(event) =>
                    setSelected((current) => ({
                      ...current,
                      [key]: event.target.value,
                    }))
                  }
                >
                  <option value="">선택 안 함</option>
                  {garments
                    .filter((item) => item.category === key)
                    .map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                </select>
                {selected[key] ? (
                  <button
                    className="text-link"
                    onClick={() =>
                      setSelected((current) => ({ ...current, [key]: "" }))
                    }
                  >
                    {label} 선택 해제
                  </button>
                ) : null}
              </div>
            ),
          )}
          <LinkButton to="upload" secondary>
            <Plus size={17} />
            사진으로 의류 추가
          </LinkButton>
          <ComingButton>피팅 결과 저장</ComingButton>
          <p className="helper">
            세션 초안은 3D 에셋이 없습니다. 레이어 숨김과 피팅 갱신은 모델 연결
            후 제공합니다.
          </p>
        </aside>
      </div>
    </>
  );
}
