import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { LinkButton, Notice, PageHeading } from "../components/UI";
import { AccountPanel } from "../features/garments/AccountPanel";
import { GarmentDetail } from "../features/garments/GarmentDetail";
import {
  OutfitLibrary,
  restoredProfile,
} from "../features/fitting/OutfitLibrary";
import { useSession } from "../stores/SessionContext";
import { categories, measurementFields } from "../types/domain";
import type { Category, Measurements } from "../types/domain";
import { newStudioDraft } from "../types/fitting";
import type {
  FitAdjustment,
  FittingInput,
  StoredProfile,
} from "../types/fitting";
import { getFitting, persistFitting, saveOutfit } from "../api/fittings";
import {
  applyHeight,
  validateMeasurements,
} from "../features/body/measurements";
import "../features/body/body.css";
import "../features/fitting/studio.css";

const FittingViewport = lazy(
  () => import("../features/fitting/FittingViewport"),
);
export function StudioPage() {
  const { auth } = useSession();
  return (
    <>
      <PageHeading
        eyebrow="YOUR FITTING SPACE"
        title="3D 피팅 스튜디오"
        description="개인 마네킹과 실제 3D 의류를 함께 확인하세요."
      />
      <Notice>
        시각적 근사 피팅입니다. 실제 착용감·압박·소재 탄성을 계산하지 않으며
        관통이 남을 수 있습니다.
      </Notice>
      <AccountPanel />
      <StudioWorkspace key={auth?.user.id ?? "guest"} />
    </>
  );
}

function StudioWorkspace() {
  const alive = useRef(false);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const {
    auth,
    garments,
    bodyProfiles,
    bodyMode,
    setBodyMode,
    setBodyProfiles,
    studio,
    setStudio,
  } = useSession();
  const draft =
    studio.owner_id === (auth?.user.id ?? null) ? studio : newStudioDraft();
  const { selected, adjustments, pins } = draft;
  const [part, setPart] = useState<Category>("top"),
    [detail, setDetail] = useState<string>();
  const [quality, setQuality] = useState<"light" | "standard">("light"),
    [reload, setReload] = useState(0);
  const [bodyConsent, setBodyConsent] = useState(false),
    [outfitName, setOutfitName] = useState("");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const profile = bodyProfiles[bodyMode],
    bodyError = validateMeasurements(profile.values);
  function choose(slot: Category, id: string) {
    setStudio({
      ...draft,
      owner_id: auth?.user.id ?? null,
      selected: { ...selected, [slot]: id },
      pins: { ...pins, [slot]: "" },
    });
  }
  function adjust(key: keyof FitAdjustment, value: number | boolean) {
    setStudio({
      ...draft,
      owner_id: auth?.user.id ?? null,
      adjustments: {
        ...adjustments,
        [part]: { ...adjustments[part], [key]: value },
      },
    });
  }
  function updateBody(key: keyof Measurements, value: string) {
    if (key === "height") {
      setBodyProfiles((profiles) => ({
        ...profiles,
        [bodyMode]: applyHeight(profile, value),
      }));
      return;
    }
    setBodyProfiles((profiles) => ({
      ...profiles,
      [bodyMode]: {
        ...profile,
        values: { ...profile.values, [key]: value },
        origins: { ...profile.origins, [key]: "user_entered" },
      },
    }));
  }
  async function persist(asOutfit: boolean) {
    if (!auth || !bodyConsent || bodyError) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const mannequin: StoredProfile = {
        mode: bodyMode,
        values: Object.fromEntries(
          Object.entries(profile.values).map(([key, value]) => [
            key,
            value === "" ? null : Number(value),
          ]),
        ) as StoredProfile["values"],
        origins: profile.origins,
      };
      const body: FittingInput = {
        mannequin,
        body_storage_consent: bodyConsent,
        slots: Object.fromEntries(
          Object.entries(selected).filter(([, id]) => !!id),
        ),
        adjustments,
      };
      const saved = await persistFitting(auth.token, body, draft.saved);
      if (!alive.current) return;
      setStudio((current) => ({
        ...current,
        owner_id: auth.user.id,
        saved: { id: saved.id, revision: saved.revision! },
        mannequin_id: saved.mannequin_id ?? undefined,
      }));
      if (asOutfit) {
        await saveOutfit(auth.token, saved.id, outfitName);
        setMessage("코디를 비공개 저장했습니다.");
      } else setMessage("피팅 설정과 최소 체형 수치를 비공개 저장했습니다.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "저장 실패");
    } finally {
      setBusy(false);
    }
  }
  async function restoreFitting() {
    if (!auth || !draft.saved) return;
    setBusy(true);
    setError("");
    try {
      const state = await getFitting(auth.token, draft.saved.id);
      if (!alive.current) return;
      if (!state.mannequin)
        throw new Error("저장된 마네킹을 찾을 수 없습니다.");
      const stored = state.mannequin;
      setBodyMode(stored.mode);
      setBodyProfiles((profiles) => ({
        ...profiles,
        [stored.mode]: restoredProfile(stored),
      }));
      const next = {
        ...draft,
        selected: {},
        pins: {},
        adjustments: state.adjustments,
        saved: { id: state.id, revision: state.revision! },
        warnings: state.warnings,
      };
      for (const key of ["top", "bottom", "outer"] as const) {
        const resource = state.slots[key];
        if (resource?.status === "available") {
          Object.assign(next.selected, { [key]: resource.garment_id });
          Object.assign(next.pins, { [key]: resource.model_asset_id });
        }
      }
      setStudio(next);
      setMessage(state.warnings.join(" ") || "피팅 설정을 복원했습니다.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "피팅 복원 실패");
    } finally {
      setBusy(false);
    }
  }
  const detailItem = garments.find((g) => g.id === detail);
  return (
    <>
      {draft.warnings?.map((warning) => (
        <p role="status" key={warning}>
          {warning}
        </p>
      ))}
      <div className="fitting-studio-layout">
        <section
          className="panel fitting-selection"
          aria-label="피팅 의류 선택"
        >
          <h2>의류 선택</h2>
          <div className="tabs" role="group" aria-label="피팅 슬롯">
            {(Object.entries(categories) as [Category, string][]).map(
              ([key, label]) => (
                <button
                  type="button"
                  key={key}
                  aria-pressed={part === key}
                  onClick={() => setPart(key)}
                >
                  {label}
                </button>
              ),
            )}
          </div>
          {(Object.entries(categories) as [Category, string][]).map(
            ([key, label]) => (
              <div
                className={`slot ${part === key ? "active-fitting-slot" : ""}`}
                key={key}
              >
                <label htmlFor={`slot-${key}`}>{label}</label>
                <select
                  id={`slot-${key}`}
                  value={selected[key] ?? ""}
                  onChange={(e) => {
                    choose(key, e.target.value);
                    setPart(key);
                  }}
                >
                  <option value="">선택 안 함</option>
                  {garments
                    .filter((g) => g.category === key)
                    .map((g) => (
                      <option key={g.id} value={g.id}>
                        {g.name}
                        {g.model_3d_status === "completed"
                          ? ""
                          : " (3D 미준비)"}
                      </option>
                    ))}
                </select>
                {selected[key] ? (
                  <div className="action-row">
                    <button
                      type="button"
                      className="text-link"
                      onClick={() => choose(key, "")}
                    >
                      {label} 선택 해제
                    </button>
                    <button
                      type="button"
                      className="text-link"
                      onClick={() => setDetail(selected[key])}
                    >
                      {label} 상세 보기
                    </button>
                  </div>
                ) : null}
              </div>
            ),
          )}
          <LinkButton to="upload" secondary>
            사진으로 의류 추가
          </LinkButton>
          <p className="helper">
            세션 초안은 GLB가 없습니다. 본인 서버 모델만 실제로 장착합니다.
            지원되는 A/B 모델은 같은 피팅 경로를 사용합니다.
          </p>
        </section>
        <section className="fitting-center">
          {bodyError ? (
            <p role="alert">{bodyError}</p>
          ) : (
            <Suspense fallback={<p role="status">피팅 3D 뷰어 준비 중…</p>}>
              <FittingViewport
                key={auth?.user.id ?? "guest"}
                profile={profile}
                token={auth?.token}
                selected={selected}
                adjustments={adjustments}
                pins={pins}
                quality={quality}
                reload={reload}
              />
            </Suspense>
          )}
        </section>
        <aside className="panel fitting-controls" aria-label="체형과 피팅 조절">
          <h2>체형·피팅 조절</h2>
          <label className="field">
            3D 품질
            <select
              value={quality}
              onChange={(e) =>
                setQuality(e.target.value as "light" | "standard")
              }
            >
              <option value="light">경량 (DPR 1)</option>
              <option value="standard">기본 (DPR 최대 1.5)</option>
            </select>
          </label>
          <details>
            <summary>체형 수정</summary>
            <label className="field">
              마네킹 체형
              <select
                value={bodyMode}
                onChange={(e) =>
                  setBodyMode(e.target.value as "manual" | "photo")
                }
              >
                <option value="manual">수동 입력 체형</option>
                <option value="photo">사진 분석 체형</option>
              </select>
            </label>
            {measurementFields.map((field) => (
              <label className="field" key={field.key}>
                {field.label} (cm)
                <input
                  type="number"
                  value={profile.values[field.key]}
                  min={field.min}
                  max={field.max}
                  step=".1"
                  onChange={(e) => updateBody(field.key, e.target.value)}
                />
              </label>
            ))}
          </details>
          <h3>{categories[part]} 조절</h3>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={adjustments[part].hidden}
              onChange={(e) => adjust("hidden", e.target.checked)}
            />
            {categories[part]} 숨기기
          </label>
          {(
            [
              ["shoulder", "어깨"],
              ["chest", "가슴"],
              ["waist", "허리"],
              ["hip", "골반"],
              ["sleeve", "소매 길이"],
              ["length", "의류 길이"],
            ] as const
          ).map(([key, label]) => (
            <label className="field" key={key}>
              {label} 보정
              <input
                type="range"
                min={key === "sleeve" || key === "length" ? 0.75 : 0.8}
                max="1.25"
                step=".01"
                value={adjustments[part][key]}
                onChange={(e) => adjust(key, Number(e.target.value))}
              />
              <span>{adjustments[part][key].toFixed(2)}배 (시각적 변형)</span>
            </label>
          ))}
          <label className="field">
            레이어 여유 (m)
            <input
              type="range"
              min="0"
              max=".06"
              step=".002"
              value={adjustments[part].clearance}
              onChange={(e) => adjust("clearance", Number(e.target.value))}
            />
          </label>
          <label className="field">
            높이 보정 (m)
            <input
              type="range"
              min="-.12"
              max=".12"
              step=".005"
              value={adjustments[part].offset_y}
              onChange={(e) => adjust("offset_y", Number(e.target.value))}
            />
          </label>
          <button
            className="button secondary"
            type="button"
            onClick={() => {
              setStudio({ ...draft, pins: {} });
              setReload((n) => n + 1);
            }}
          >
            모델 다시 불러오기
          </button>
        </aside>
      </div>
      <section className="panel" aria-label="피팅과 코디 저장">
        <h2>피팅·코디 저장</h2>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={bodyConsent}
            onChange={(e) => setBodyConsent(e.target.checked)}
          />
          같은 마네킹 복원을 위해 최소 체형 수치·출처·의류 조합·조절값을 내
          계정에 비공개 저장하는 데 동의합니다.
        </label>
        <p className="helper">
          기본 편집은 탭 메모리입니다. 원본 신체 사진·관절·얼굴을 서버로 보내지
          않습니다.
        </p>
        <label className="field">
          코디 이름
          <input
            value={outfitName}
            maxLength={80}
            onChange={(e) => setOutfitName(e.target.value)}
          />
        </label>
        <div className="action-row">
          <button
            className="button secondary"
            type="button"
            disabled={!auth || !bodyConsent || busy || !!bodyError}
            onClick={() => void persist(false)}
          >
            피팅 설정 저장
          </button>
          <button
            className="button secondary"
            type="button"
            disabled={!auth || !draft.saved || busy}
            onClick={() => void restoreFitting()}
          >
            저장된 피팅 불러오기
          </button>
          <button
            className="button primary"
            type="button"
            disabled={
              !auth || !bodyConsent || busy || !outfitName.trim() || !!bodyError
            }
            onClick={() => void persist(true)}
          >
            현재 코디 저장
          </button>
        </div>
        {message ? <p role="status">{message}</p> : null}
        {error ? <p role="alert">{error}</p> : null}
      </section>
      <OutfitLibrary key={`${auth?.user.id ?? "guest"}-${message}`} />
      {detailItem ? (
        <GarmentDetail
          key={detailItem.id}
          item={detailItem}
          onClose={() => setDetail(undefined)}
        />
      ) : null}
    </>
  );
}
