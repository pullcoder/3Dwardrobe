import { lazy, Suspense, useEffect, useRef, useState } from "react";
import {
  Check,
  Fingerprint,
  RotateCcw,
  Ruler,
  Save,
  Trash2,
} from "lucide-react";
import { PhotoPicker } from "../components/PhotoPicker";
import { LinkButton, Notice, PageHeading, Panel } from "../components/UI";
import { useSession } from "../stores/SessionContext";
import { measurementFields } from "../types/domain";
import type { Measurements } from "../types/domain";
import {
  applyHeight,
  createBodyProfiles,
  profileFromPose,
  validateMeasurements,
} from "../features/body/measurements";
import { analyzePose } from "../features/body/poseClient";
import { BodyVault } from "../features/body/BodyVault";
import { PosePlot } from "../features/body/PosePlot";
import type { BodyMode, PoseAnalysis } from "../features/body/types";
import "../features/body/body.css";

const MannequinViewport = lazy(
  () => import("../features/mannequin/MannequinViewport"),
);

export function BodyPage({ mannequin = false }: { mannequin?: boolean }) {
  const {
    bodyProfiles,
    setBodyProfiles,
    bodyMode: mode,
    setBodyMode,
    bodyPhoto,
    setBodyPhoto,
  } = useSession();
  const [rights, setRights] = useState(false);
  const [removeOriginal, setRemoveOriginal] = useState(true);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [analysis, setAnalysis] = useState<PoseAnalysis>();
  const controller = useRef<AbortController | null>(null);
  const profile = bodyProfiles[mode];
  const validationError = validateMeasurements(profile.values);
  useEffect(() => () => controller.current?.abort(), []);

  function switchMode(next: BodyMode) {
    controller.current?.abort();
    setBodyMode(next);
    setError("");
    setMessage("");
  }
  function update(key: keyof Measurements, value: string) {
    setMessage("");
    setError("");
    setBodyProfiles((profiles) => ({
      ...profiles,
      [mode]:
        key === "height"
          ? applyHeight(profiles[mode], value)
          : {
              ...profiles[mode],
              saved_at: undefined,
              values: { ...profiles[mode].values, [key]: value },
              origins: {
                ...profiles[mode].origins,
                [key]: value ? "user_entered" : undefined,
              },
            },
    }));
  }
  async function analyze() {
    if (!bodyPhoto || !rights) return;
    if (!profile.values.height || validationError) {
      setError(validationError || "키를 먼저 입력해 주세요.");
      return;
    }
    const next = new AbortController();
    controller.current?.abort();
    controller.current = next;
    const analysisHeight = profile.values.height;
    setBusy(true);
    setError("");
    setMessage("");
    setAnalysis(undefined);
    setProgress("사진을 기기 안에서 준비하고 있어요.");
    try {
      const result = await analyzePose(bodyPhoto, setProgress, next.signal);
      if (next.signal.aborted) return;
      setBodyProfiles((profiles) => ({
        ...profiles,
        photo: profileFromPose(result.summary, analysisHeight),
      }));
      setAnalysis(result);
      if (removeOriginal) setBodyPhoto(undefined);
      setMessage(
        `33개 특징점을 추출했습니다. 길이는 2D 투영 기반 추정값입니다.${removeOriginal ? " 원본 사진을 앱 메모리에서 제거했습니다." : " 원본 사진은 이 탭에서만 유지합니다."}`,
      );
    } catch (reason) {
      if (!next.signal.aborted)
        setError(
          reason instanceof Error
            ? reason.message
            : "분석하지 못했습니다. 다시 시도해 주세요.",
        );
    } finally {
      if (controller.current === next) {
        setBusy(false);
        setProgress("");
        controller.current = null;
      }
    }
  }
  function validateCurrent() {
    if (validationError) {
      setError("");
      return false;
    }
    if (!profile.values.height) {
      setError("키를 입력해 주세요.");
      return false;
    }
    if (mode === "photo" && !profile.ratios) {
      setError(
        "사진을 먼저 분석해 주세요. 사진 없이 만들려면 수동 입력 체형을 선택하세요.",
      );
      return false;
    }
    setError("");
    return true;
  }
  function reset() {
    controller.current?.abort();
    setBusy(false);
    setProgress("");
    setAnalysis(undefined);
    setBodyProfiles((profiles) => ({
      ...profiles,
      [mode]: createBodyProfiles()[mode],
    }));
    if (mode === "photo") setBodyPhoto(undefined);
    setError("");
    setMessage(
      "현재 체형을 삭제하고 기본 마네킹 비율로 초기화했습니다. 기기 보관함은 별도로 삭제해 주세요.",
    );
  }
  const feedback = (
    <>
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
      {message ? (
        <p className="success" role="status">
          {message}
        </p>
      ) : null}
    </>
  );
  return (
    <>
      <PageHeading
        eyebrow={mannequin ? "MY DIGITAL SELF" : "BODY PROFILE"}
        title={mannequin ? "3D 마네킹 편집" : "내 몸을 이해하는 첫걸음"}
        description="사진 분석 체형과 직접 입력한 체형을 따로 준비하고, 나만의 중립 마네킹으로 확인하세요."
      />
      <Notice>
        사진·치수를 정확한 신체 측정으로 표시하지 않습니다. 관절은 MediaPipe
        추출, 길이는 투영 기반 추정이며 둘레는 직접 입력합니다. 의복 제거·숨겨진
        체형 복원·실제 얼굴 복원은 수행하지 않습니다.
      </Notice>
      <ol className="body-steps">
        <li>사진 또는 수동 입력</li>
        <li>기기 내 분석</li>
        <li>추정값 확인·수정</li>
        <li>3D 확인·저장</li>
      </ol>
      <div
        className="segmented body-mode"
        role="group"
        aria-label="체형 입력 방식"
      >
        <button
          aria-pressed={mode === "manual"}
          className={mode === "manual" ? "selected" : ""}
          disabled={busy}
          onClick={() => switchMode("manual")}
        >
          <Ruler size={16} />
          수동 입력 체형
        </button>
        <button
          aria-pressed={mode === "photo"}
          className={mode === "photo" ? "selected" : ""}
          disabled={busy}
          onClick={() => switchMode("photo")}
        >
          <Fingerprint size={16} />
          사진 분석 체형
        </button>
      </div>
      <div className="body-workspace">
        <div className="body-viewer">
          <Suspense
            fallback={
              <div className="panel" role="status">
                3D 뷰어를 준비하고 있어요.
              </div>
            }
          >
            <MannequinViewport profile={profile} />
          </Suspense>
          <div className="body-source-note">
            <strong>
              {mode === "photo" ? "사진 분석 체형" : "수동 입력 체형"}
            </strong>
            <span>
              {profile.saved_at
                ? `탭에 저장됨 · ${new Date(profile.saved_at).toLocaleTimeString("ko-KR")}`
                : "편집 중 · 저장 전"}
            </span>
            <p>
              미입력 항목은 기본 비율로 표시합니다. 형태는 타원·캡슐 기반
              근사이며 의류 피팅 결과가 아닙니다.
            </p>
          </div>
        </div>
        <div className="body-editor">
          {mode === "photo" ? (
            <Panel
              title="01. 전신 사진 분석"
              subtitle="본인 한 명, 정면으로 서서 팔을 조금 띄우고 정수리·손목·발끝까지 여백 있게 촬영해 주세요."
            >
              <label className="field photo-height">
                <span>
                  키<small>직접 입력 · 분석에 필요</small>
                </span>
                <div className="input-unit">
                  <input
                    type="number"
                    min={80}
                    max={250}
                    step="0.1"
                    placeholder="키를 먼저 입력해 주세요"
                    value={profile.values.height}
                    disabled={busy}
                    onChange={(e) => update("height", e.target.value)}
                  />
                  <span>cm</span>
                </div>
              </label>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={rights}
                  disabled={busy}
                  onChange={(e) => {
                    setRights(e.target.checked);
                    if (!e.target.checked) {
                      setBodyPhoto(undefined);
                      setAnalysis(undefined);
                    }
                  }}
                />
                본인 사진이며 기기 내 분석에 동의합니다.
              </label>
              {rights ? (
                <PhotoPicker
                  label="정면 전신 사진"
                  hint="JPEG·PNG·WebP / 10 MiB·20MP 이하"
                  file={bodyPhoto}
                  disabled={busy}
                  required
                  onChange={(file) => {
                    setBodyPhoto(file);
                    setAnalysis(undefined);
                    setError("");
                    setMessage("");
                  }}
                />
              ) : (
                <p className="helper">
                  동의 후 사진을 선택할 수 있어요. 원본은 서버나 외부 AI에
                  전송하지 않습니다.
                </p>
              )}
              <label className="checkbox-row original-removal">
                <input
                  type="checkbox"
                  checked={removeOriginal}
                  disabled={busy}
                  onChange={(e) => setRemoveOriginal(e.target.checked)}
                />
                분석 성공 후 원본 사진을 앱에서 제거 (기본)
              </label>
              <button
                type="button"
                className="button primary"
                disabled={
                  !bodyPhoto ||
                  !rights ||
                  busy ||
                  !profile.values.height ||
                  !!validationError
                }
                onClick={() => void analyze()}
              >
                {busy ? "분석 중…" : "MediaPipe 분석"}
              </button>
              {busy ? (
                <>
                  <p className="helper" role="status">
                    {progress}
                  </p>
                  <button
                    className="text-link"
                    onClick={() => {
                      controller.current?.abort();
                      setMessage("분석을 취소했습니다.");
                    }}
                  >
                    분석 취소
                  </button>
                </>
              ) : null}
              {bodyPhoto ? (
                <button
                  className="button secondary danger"
                  disabled={busy}
                  onClick={() => {
                    setBodyPhoto(undefined);
                    setAnalysis(undefined);
                    setMessage(
                      "원본 사진을 앱에서 제거했습니다. 분석 체형은 유지합니다.",
                    );
                  }}
                >
                  <Trash2 size={15} />
                  원본 사진 삭제
                </button>
              ) : null}
              {analysis ? <PosePlot analysis={analysis} /> : null}
              {feedback}
              {profile.ratios ? (
                <p className="helper">
                  어깨/키 {(profile.ratios.shoulder * 100).toFixed(1)}% ·
                  몸통/키 {(profile.ratios.torso * 100).toFixed(1)}% · 평균 관절
                  가시성 {(profile.ratios.mean_visibility * 100).toFixed(0)}%
                  (치수 정확도 아님)
                </p>
              ) : null}
            </Panel>
          ) : null}
          <Panel
            title={
              mode === "photo"
                ? "02. 추정값 확인 및 치수 보정"
                : "신체 치수 직접 입력"
            }
            subtitle="단위 cm · 팔은 어깨 관절~손목, 다리는 골반 관절~발목입니다. 둘레와 의류 단면 너비를 혼동하지 마세요."
          >
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (validateCurrent())
                  setMessage(
                    "직접 입력한 치수를 이 탭에 반영했습니다. 서버에는 저장하지 않았습니다.",
                  );
              }}
            >
              <div className="form-grid">
                {measurementFields
                  .filter((field) => mode !== "photo" || field.key !== "height")
                  .map((field) => (
                    <label className="field" key={field.key}>
                      <span>
                        {field.label}
                        <small>
                          {profile.origins[field.key] === "estimated"
                            ? "사진 추정값"
                            : profile.values[field.key]
                              ? "직접 입력"
                              : "미입력 · 기본 비율"}
                        </small>
                      </span>
                      <div className="input-unit">
                        <input
                          type="number"
                          min={field.min}
                          max={field.max}
                          step="0.1"
                          placeholder="입력 전"
                          value={profile.values[field.key]}
                          disabled={busy}
                          onChange={(e) => update(field.key, e.target.value)}
                        />
                        <span>cm</span>
                      </div>
                    </label>
                  ))}
              </div>
              <div className="action-row">
                <button
                  type="submit"
                  className="button secondary"
                  disabled={busy}
                >
                  <Check size={16} />
                  입력값 확인
                </button>
                <button
                  type="button"
                  className="button primary"
                  disabled={busy}
                  onClick={() => {
                    if (validateCurrent())
                      setMessage(
                        "현재 치수로 3D 마네킹을 갱신했습니다. 정확한 신체 복원 결과는 아닙니다.",
                      );
                  }}
                >
                  마네킹 생성·갱신
                </button>
              </div>
            </form>
            {validationError ? (
              <p className="error" role="alert">
                {validationError}
              </p>
            ) : null}
            <p className="helper">
              사진 모드에서 키를 바꾸면 사진 추정 길이가 갱신됩니다. 직접 수정한
              길이는 유지합니다. 추정값 초기화는 재분석으로 수행합니다.
            </p>
            <div className="action-row">
              <button
                className="button primary"
                disabled={busy}
                onClick={() => {
                  if (!validateCurrent()) return;
                  setBodyProfiles((profiles) => ({
                    ...profiles,
                    [mode]: {
                      ...profiles[mode],
                      saved_at: new Date().toISOString(),
                    },
                  }));
                  setMessage(
                    "현재 체형을 이 탭에 저장했습니다. 반대 모드의 체형은 유지합니다.",
                  );
                }}
              >
                <Save size={16} />
                체형 저장 (이 탭)
              </button>
              <button
                className="button secondary"
                disabled={busy}
                onClick={reset}
              >
                <RotateCcw size={16} />
                기본 마네킹으로 초기화
              </button>
              <button
                className="button secondary danger"
                disabled={busy}
                onClick={reset}
              >
                <Trash2 size={15} />
                현재 체형 삭제
              </button>
            </div>
            {profile.saved_at ? (
              <div className="studio-link">
                <LinkButton to="studio">
                  저장한 체형으로 스튜디오 이동
                </LinkButton>
              </div>
            ) : null}
          </Panel>
        </div>
      </div>
      {mode === "manual" ? feedback : null}
      <BodyVault
        disabled={busy}
        onRestore={() => {
          controller.current?.abort();
          setAnalysis(undefined);
        }}
      />
    </>
  );
}
