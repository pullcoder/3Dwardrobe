import { useState } from "react";
import { ArrowRight, Upload } from "lucide-react";
import { validateUpload } from "../api/client";
import { hydrateGarment, saveGarment } from "../api/garments";
import { PhotoPicker } from "../components/PhotoPicker";
import { Notice, PageHeading, Panel, PrivacyNote } from "../components/UI";
import { AccountPanel } from "../features/garments/AccountPanel";
import { AnalysisPanel } from "../features/garments/AnalysisPanel";
import { GarmentEditor } from "../features/garments/GarmentEditor";
import { blankInfo } from "../features/garments/types";
import type { Analysis, GarmentInfo } from "../features/garments/types";
import { useSession } from "../stores/SessionContext";
import type { Photos, PhotoSlot } from "../types/domain";

const slots: { key: PhotoSlot; label: string; hint: string }[] = [
  { key: "front", label: "앞면 사진", hint: "중앙에 의류 한 벌의 전체 모습" },
  { key: "back", label: "뒷면 사진", hint: "뒷면 디자인을 담은 사진" },
  { key: "size", label: "사이즈표 사진", hint: "치수와 단위가 선명한 사진" },
  {
    key: "material",
    label: "소재 및 성분표 사진",
    hint: "라벨을 가까이 찍은 사진",
  },
];
export function UploadPage() {
  const { auth, setGarments } = useSession();
  const [photos, setPhotos] = useState<Photos>({});
  const [rights, setRights] = useState(false);
  const [serverConsent, setServerConsent] = useState(false);
  const [storageConsent, setStorageConsent] = useState(false);
  const [info, setInfo] = useState<GarmentInfo>(blankInfo);
  const [analysis, setAnalysis] = useState<Analysis>({});
  const [cutouts, setCutouts] = useState<
    Partial<Record<"front" | "back", File>>
  >({});
  const [busy, setBusy] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState("");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const locked = busy || analyzing;
  function changePhotos(next: Photos) {
    setPhotos(next);
    setAnalysis({});
    setCutouts({});
    setRevision((n) => n + 1);
    setSaved(false);
    setResult("");
    setError("");
  }
  function complete() {
    changePhotos({});
    setInfo(blankInfo);
    setServerConsent(false);
    setStorageConsent(false);
    setSaved(true);
  }
  async function validate() {
    if (!photos.front || !rights || !serverConsent) return;
    setBusy(true);
    setError("");
    setResult("");
    try {
      const r = await validateUpload(photos.front);
      setResult(
        `앞면 사진 형식 검증 완료 · ${r.width} × ${r.height}px · 서버 보관 안 함 · AI 분석 안 함`,
      );
    } catch (e) {
      setError(
        e instanceof Error && e.message !== "Failed to fetch"
          ? e.message
          : "로컬 API에 연결할 수 없습니다. 백엔드 실행 상태를 확인해 주세요.",
      );
    } finally {
      setBusy(false);
    }
  }
  function draft() {
    if (!photos.front || !rights || !info.name.trim()) return;
    setGarments((items) => [
      ...items,
      {
        ...info,
        id: crypto.randomUUID(),
        name: info.name.trim(),
        photos: { ...photos, front: photos.front! },
        info,
        analysis,
        cutouts,
        created_at: new Date().toISOString(),
        source: "user_entered",
      },
    ]);
    complete();
  }
  async function save() {
    if (
      !auth ||
      !storageConsent ||
      !rights ||
      !photos.front ||
      !info.name.trim()
    )
      return;
    setBusy(true);
    setError("");
    try {
      const item = await saveGarment(
        auth.token,
        info,
        analysis,
        photos,
        cutouts,
      );
      const hydrated = await hydrateGarment(auth.token, item);
      setGarments((items) => [...items, hydrated]);
      complete();
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "저장하지 못했습니다. 다시 시도해 주세요.",
      );
    } finally {
      setBusy(false);
    }
  }
  function applyAnalysis(
    next: Analysis,
    files: typeof cutouts,
    patch: Partial<GarmentInfo>,
  ) {
    setAnalysis(next);
    setCutouts(files);
    setInfo((current) => {
      const updated = { ...current };
      // 재분석은 기존 사용자 수정값을 덮어쓰지 않는다. 제안 원본은 JSON에 보존한다.
      for (const key of [
        "garment_type",
        "color",
        "pattern",
        "sleeve",
        "neckline",
        "size",
        "material",
      ] as const) {
        const candidate = patch[key];
        if (candidate && ["", "unknown", "미확인"].includes(current[key]))
          updated[key] = candidate;
      }
      if (patch.category && !current.name) updated.category = patch.category;
      if (patch.measurements)
        updated.measurements = [
          ...current.measurements.filter((m) => m.source === "user_entered"),
          ...patch.measurements,
        ];
      if (patch.composition)
        updated.composition = [
          ...current.composition.filter((c) => c.source === "user_entered"),
          ...patch.composition,
        ];
      return updated;
    });
  }
  return (
    <>
      <PageHeading
        eyebrow="ADD TO YOUR WARDROBE"
        title="내 옷의 새로운 시작"
        description="옷 한 벌의 사진을 분석하고, 직접 확인한 정보로 나만의 옷장을 채워 보세요."
      />
      <Notice>
        분류·배경 제거·OCR은 로컬 AI 모델로 처리합니다. 인식이 불명확한 값은
        미확인으로 두고 직접 수정하세요. 3D 의류 생성과 가상 피팅은 아직
        제공하지 않습니다.
      </Notice>
      {!locked ? <AccountPanel /> : null}
      <Panel
        title="01. 의류 사진"
        subtitle="직접 촬영한 의류 한 벌을 권장해요. JPG · PNG · WebP, 한 장당 10 MiB · 20MP 이하. 드래그해서 놓거나 사진을 선택하세요."
      >
        <label className="checkbox-row rights-check">
          <input
            type="checkbox"
            checked={rights}
            disabled={locked}
            onChange={(e) => {
              setRights(e.target.checked);
              if (!e.target.checked) {
                changePhotos({});
                setServerConsent(false);
                setStorageConsent(false);
              }
            }}
          />
          직접 촬영했거나 적법한 이용 권한이 있는 사진입니다.
        </label>
        {rights ? (
          <div className="photo-grid">
            {slots.map((slot) => (
              <PhotoPicker
                key={slot.key}
                label={slot.label}
                hint={slot.hint}
                required={slot.key === "front"}
                disabled={locked}
                file={photos[slot.key]}
                onChange={(file) =>
                  changePhotos({ ...photos, [slot.key]: file })
                }
              />
            ))}
          </div>
        ) : (
          <div className="upload-locked">
            <Upload size={26} />
            <p>사진 이용 권리를 확인하면 사진을 선택할 수 있어요.</p>
          </div>
        )}
        <PrivacyNote />
      </Panel>
      <AnalysisPanel
        key={`${revision}-${auth?.user.id ?? "guest"}`}
        token={auth?.token}
        photos={photos}
        onResult={applyAnalysis}
        onBusy={setAnalyzing}
        disabled={busy}
      />
      <Panel
        title="03. 분석 결과 확인 및 정보 수정"
        subtitle="자동 제안은 추정값입니다. 수정한 정보는 원본 분석과 별도로 저장하고, 이후 3D 복원 입력으로 활용할 수 있습니다."
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            draft();
          }}
        >
          <GarmentEditor value={info} onChange={setInfo} disabled={locked} />
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={storageConsent}
              disabled={locked}
              onChange={(e) => setStorageConsent(e.target.checked)}
            />
            선택한 원본·누끼·분석·수정 정보를 로컬 서버의 내 비공개 옷장에
            저장합니다. 삭제할 때까지 보관합니다.
          </label>
          <div className="action-row">
            <button
              type="button"
              className="button primary"
              disabled={
                locked ||
                !auth ||
                !storageConsent ||
                !rights ||
                !photos.front ||
                !info.name.trim() ||
                info.composition.some((c) => !c.name.trim())
              }
              onClick={() => void save()}
            >
              {busy ? "저장 처리 중…" : "디지털 옷장에 저장"}
            </button>
            <button
              type="submit"
              className="button secondary"
              disabled={locked || !photos.front || !rights || !info.name.trim()}
            >
              세션 초안에 추가
            </button>
          </div>
          <p className="helper">
            사이즈표와 소재표 없이도 등록할 수 있습니다. 로그인하지 않으면 탭
            초안만 사용할 수 있어요. 새로고침 시 초안은 사라집니다.
          </p>
        </form>
        {saved ? (
          <div role="status" className="success">
            의류를 추가했습니다.{" "}
            <a href="#/closet">
              옷장에서 확인하기 <ArrowRight size={14} />
            </a>
          </div>
        ) : null}
        {error ? (
          <p role="alert" className="error">
            {error}
          </p>
        ) : null}
      </Panel>
      <Panel
        title="선택: 로컬 서버 파일 검증"
        subtitle="앞면 사진 한 장의 형식·해상도만 확인한 뒤 폐기합니다. AI 분석 버튼과 별개의 기능입니다."
      >
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={serverConsent}
            disabled={locked}
            onChange={(e) => setServerConsent(e.target.checked)}
          />
          선택한 앞면 사진을 로컬 개발 API로 보내 형식을 확인합니다.
        </label>
        <button
          type="button"
          className="button secondary"
          disabled={!photos.front || !rights || !serverConsent || locked}
          onClick={() => void validate()}
        >
          앞면 사진 형식 검증
        </button>
        {result ? (
          <p role="status" className="success">
            {result}
          </p>
        ) : null}
      </Panel>
    </>
  );
}
