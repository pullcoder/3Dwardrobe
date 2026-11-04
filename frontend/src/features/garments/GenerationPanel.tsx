import { lazy, Suspense, useEffect, useState } from "react";
import {
  confirmPhotoRights,
  deleteModel,
  generateModel,
  getGeneration,
  getModel,
  withdrawRights,
  analyzeGarmentSilhouette,
} from "../../api/garments";
import type { GenerationState, RightStatus } from "./types";
import { useSession } from "../../stores/SessionContext";
import { checkImage } from "../../lib/images";

const GarmentModelViewer = lazy(() => import("./GarmentModelViewer"));
const rightsText: Record<RightStatus, string> = {
  unverified: "미확인",
  confirmed: "사용자 확인",
  pending: "검토 중",
  verified: "증빙 검증",
  rejected: "거절",
  disputed: "신고·철회 검토",
};
const states = {
  idle: "생성 전",
  queued: "대기 중",
  processing: "생성 중",
  completed: "생성 완료",
  failed: "생성 실패",
  cancelled: "취소됨",
};
const stageText: Record<string, string> = {
  preprocessing: "의류 이미지 전처리",
  inference: "AI 모델 생성",
  postprocessing: "메시 후처리·착용 구조 검사",
  mesh: "메시·재질 생성",
  exporting: "GLB 내보내기",
  validating: "GLB 검증",
  saving: "비공개 저장",
  asset_storage: "모델 저장",
  database_update: "모델 경로 갱신",
  database_commit: "저장 확정",
};

export function GenerationPanel({
  token,
  id,
  garmentType,
}: {
  token: string;
  id: string;
  garmentType: string;
}) {
  const { setGarments } = useSession();
  const [state, setState] = useState<GenerationState>();
  const [bytes, setBytes] = useState<ArrayBuffer>();
  const [error, setError] = useState("");
  const [pollError, setPollError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [shapePhoto, setShapePhoto] = useState<File>();
  const [shapeConsent, setShapeConsent] = useState(false);
  const [engine, setEngine] = useState<"template" | "triposr" | "trellis2">(
    "template",
  );
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const result = await getGeneration(token, id, controller.signal);
        if (!controller.signal.aborted) {
          setPollError("");
          setState(result);
          if (!result.model_ready) setBytes(undefined);
          setGarments((items) =>
            items.some(
              (g) =>
                g.id === id && g.model_3d_status !== result.generation_status,
            )
              ? items.map((g) =>
                  g.id === id
                    ? { ...g, model_3d_status: result.generation_status }
                    : g,
                )
              : items,
          );
        }
      } catch (e) {
        if (!controller.signal.aborted)
          setPollError(
            e instanceof Error ? e.message : "작업 상태를 조회하지 못했습니다.",
          );
      } finally {
        if (!controller.signal.aborted)
          timer = setTimeout(() => void poll(), 1500);
      }
    }
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [token, id, refresh, setGarments]);
  const ready = state?.model_ready;
  const jobId = state?.job_id;
  useEffect(() => {
    if (!ready) return;
    const controller = new AbortController();
    void getModel(token, id, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setBytes(data);
      })
      .catch((e) => {
        if (!controller.signal.aborted)
          setError(
            e instanceof Error ? e.message : "모델을 불러오지 못했습니다.",
          );
      });
    return () => controller.abort();
  }, [token, id, ready, jobId]);
  async function act(task: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await task();
      setBytes(undefined);
      setState(await getGeneration(token, id));
      setRefresh((n) => n + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "요청에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }
  const active =
    state?.generation_status === "queued" ||
    state?.generation_status === "processing";
  const unsupported = state && !state.supported_types.includes(garmentType);
  const bUnavailable = state?.selected_mode === "B" && !state.b_available;
  return (
    <section aria-label="의류 3D 복원">
      <h3>의류 3D 복원</h3>
      <p>
        A모드: 일반적인 형태·색상을 반영한 독립 3D 의류. B모드: 증빙으로 이용
        권한이 검증된 티셔츠·바지 사진의 색과 무늬를 3D 표면에 반영합니다. 앞·뒤
        사진이 있으면 각각 사용하며, 고정밀 입체 복원은 아닙니다.
      </p>
      <p className="helper">
        A도 적법한 입력·처리 권한이 필요하며 모든 디자인의 법적 안전성을
        보장하지 않습니다. A에서는 사진 텍스처·로고·일러스트를 복사하지
        않습니다. 저장된 분석/수정 정보를 사용하므로 변경한 정보는 먼저
        저장하세요.
      </p>
      {state ? (
        <>
          <p>
            사진 권한: {rightsText[state.photo_rights_status]} · 디자인 복원:{" "}
            {rightsText[state.detailed_rights_status]} · 결과 저장·이용:{" "}
            {rightsText[state.output_rights_status]}
          </p>
          <p>자동 선택 모드: {state.selected_mode ?? "권한 확인 후 결정"}</p>
          {state.selected_mode === "A" ? (
            <p className="helper">
              현재는 일반형 A모드입니다. 사진의 색·무늬까지 반영하려면 앞면·뒷면
              사진을 보관하고 아래 권리 검토에서 세 권한을 검증해야 합니다.
            </p>
          ) : null}
          <label className="field">
            3D 생성 엔진
            <select
              value={engine}
              disabled={busy || active}
              onChange={(event) =>
                setEngine(event.target.value as typeof engine)
              }
            >
              {(
                state.engines ?? [
                  { id: "template", name: "기존 의류 템플릿", available: true },
                ]
              ).map((item) => (
                <option
                  key={item.id}
                  value={item.id}
                  disabled={!item.available}
                >
                  {item.name}
                  {item.available ? "" : " · 사용 불가"}
                </option>
              ))}
            </select>
          </label>
          <p className="helper">
            엔진과 A/B 권리 모드는 별개입니다. AI 생성만으로 원본 디자인의 이용
            권한이나 착용 구조가 검증되지 않습니다.
          </p>
          {state.engines
            ?.filter((item) => !item.available)
            .map((item) => (
              <details key={item.id}>
                <summary>{item.name} 사용 불가 사유</summary>
                <p>{item.requirements}</p>
                <ul>
                  {item.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </details>
            ))}
          {state.model_metadata?.generation_kind === "ai" ? (
            <p role="status">
              AI 생성 메시입니다. 착용 구조가 미검증되어 자동 피팅을 보류합니다.
              피팅하려면 기존 의류 템플릿으로 다시 생성하세요.
            </p>
          ) : null}
          <p role="status">
            작업 상태: {states[state.generation_status]}
            {state.generation_status === "processing"
              ? ` · ${stageText[state.stage] ?? "작업 처리"}`
              : ""}
          </p>
          {!state.runtime?.worker_online ? (
            <p role="status" className="helper">
              3D 생성 워커의 응답이 없습니다. 생성 요청은 대기열에 보관됩니다.
              서버에서 API와 생성 워커를 함께 실행해야 처리됩니다. 워커를 다시
              연결하면 대기 요청을 처리합니다.
            </p>
          ) : null}
          {state.failure ? (
            <p role="alert">
              실패 단계: {stageText[state.failure.stage ?? ""] ?? "미확인"} ·
              예외 유형: {state.failure.exception_type ?? "미확인"}. 정보를
              확인하고 재시도해 주세요.
            </p>
          ) : null}
          {active ? (
            <p className="helper">
              백그라운드 처리 중입니다. 대기 상태가 계속되면 생성 워커 실행
              상태를 확인해 주세요. 새로고침 후에도 작업 상태를 불러올 수
              있습니다.
            </p>
          ) : null}
          {state.photo_rights_status === "unverified" ? (
            <>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                />
                이 의류 사진의 입력·처리에 필요한 이용 권한을 확인했습니다.
              </label>
              <button
                type="button"
                className="button secondary"
                disabled={!confirmed || busy}
                onClick={() => void act(() => confirmPhotoRights(token, id))}
              >
                사진 이용 권한 확인
              </button>
            </>
          ) : null}
          {!state.selected_mode ? (
            <p>
              권한 미확인 또는 신고·철회 상태로 복원을 보류합니다. 증빙 검토가
              필요합니다.
            </p>
          ) : null}
          {bUnavailable ? (
            <p>
              사진 외형을 반영하려면 티셔츠·바지 앞면 사진을 보관하고 세 권한을
              검증해야 합니다. 사진이 없는 기존 등록은 보관 동의로 다시
              등록하세요.
            </p>
          ) : null}
          {["티셔츠", "청바지", "슬랙스", "반바지"].includes(garmentType) ? (
            <section
              aria-label={
                garmentType === "티셔츠"
                  ? "티셔츠 실루엣 분석"
                  : "바지 실루엣 분석"
              }
            >
              <h4>사진 외곽을 의류 템플릿에 반영</h4>
              <p>
                저장한 누끼·앞면은 생성 시 분석합니다. 원본을 보관하지 않았다면
                아래에 정면 사진이나 누끼 PNG를 다시 입력하세요. 사진은 이 분석
                후 저장하지 않고 외곽 수치만 비공개 기록합니다.
              </p>
              <label className="field">
                형태 분석용 의류 사진
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  disabled={busy || active}
                  onChange={(event) => {
                    setShapePhoto(event.target.files?.[0]);
                    setShapeConsent(false);
                  }}
                  style={{
                    position: "static",
                    opacity: 1,
                    width: "100%",
                    height: "auto",
                  }}
                />
              </label>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  disabled={busy || active}
                  checked={shapeConsent}
                  onChange={(event) => setShapeConsent(event.target.checked)}
                />
                이 사진의 이용 권한을 확인했으며 형태 분석을 위해 로컬 서버로
                전송하는 데 동의합니다.
              </label>
              <button
                className="button secondary"
                type="button"
                disabled={
                  busy ||
                  active ||
                  !shapePhoto ||
                  !shapeConsent ||
                  !state.selected_mode
                }
                onClick={() =>
                  void act(async () => {
                    if (!shapePhoto) return;
                    await checkImage(shapePhoto);
                    const result = await analyzeGarmentSilhouette(
                      token,
                      id,
                      shapePhoto,
                    );
                    setGarments((items) =>
                      items.map((item) =>
                        item.id === id
                          ? {
                              ...item,
                              revision: result.revision,
                              model_3d_status: "cancelled",
                            }
                          : item,
                      ),
                    );
                    setShapePhoto(undefined);
                    setShapeConsent(false);
                  })
                }
              >
                사진 외곽 분석
              </button>
              <button
                className="button secondary"
                type="button"
                disabled={busy || !shapePhoto}
                onClick={() => {
                  setShapePhoto(undefined);
                  setShapeConsent(false);
                }}
              >
                분석 사진 삭제
              </button>
            </section>
          ) : null}
          {unsupported ? (
            <p>
              현재 미지원 의류입니다. 지원 종류:{" "}
              {state.supported_types.join(", ")}
            </p>
          ) : null}
          <div className="action-row">
            <button
              type="button"
              className="button primary"
              disabled={
                busy ||
                active ||
                !state.selected_mode ||
                bUnavailable ||
                unsupported
              }
              onClick={() => void act(() => generateModel(token, id, engine))}
            >
              {state.generation_status === "failed"
                ? "3D 생성 재시도"
                : state.model_ready
                  ? "3D 모델 재생성"
                  : "3D 모델 생성"}
            </button>
            <button
              type="button"
              className="button secondary"
              disabled={busy || (!state.model_ready && !active)}
              onClick={() => void act(() => deleteModel(token, id))}
            >
              3D 모델 삭제·작업 취소
            </button>
            <button
              type="button"
              className="button secondary"
              disabled={busy || !state.selected_mode}
              onClick={() => void act(() => withdrawRights(token, id))}
            >
              이용 권한 철회
            </button>
          </div>
          {state.generation_error ? (
            <p role="alert">
              {state.generation_error === "GENERATION_FAILED"
                ? "모델 생성에 실패했습니다. 정보를 확인하고 재시도해 주세요."
                : state.generation_error === "WORKER_TIMEOUT"
                  ? "워커가 응답하지 않아 생성에 실패했습니다. 재시도할 수 있습니다."
                  : state.generation_error === "SOURCE_UNAVAILABLE"
                    ? "허용된 원본 사진을 찾지 못했습니다. 원본 보관 및 권한을 확인해 주세요."
                    : "정보·권한 변경 또는 삭제 요청으로 이전 작업과 모델이 무효화되었습니다."}
            </p>
          ) : null}
          {busy ? <p role="status">요청 처리 중…</p> : null}
          {bytes && state.model_ready && !busy ? (
            <Suspense fallback={<p>3D 뷰어 준비 중…</p>}>
              <GarmentModelViewer key={jobId} bytes={bytes} />
            </Suspense>
          ) : null}
          {state.model_metadata ? (
            <details>
              <summary>모델 정보와 추정 치수</summary>
              {state.model_metadata.photo_appearance ? (
                <p>
                  사진 외형 반영 · 앞면: 검증된 사진 · 뒷면:{" "}
                  {state.model_metadata.photo_appearance.back ===
                  "verified_photo"
                    ? "검증된 사진"
                    : "사진 없음, 일반 원단 추정"}
                  . 옆면과 깊이는 추정입니다.
                </p>
              ) : null}
              <p>
                단위: 미터 · Y-up / Z-front · 후면/깊이 추정 · 물리 시뮬레이션
                없음
              </p>
              <ul>
                {Object.entries(state.model_metadata.dimensions).map(
                  ([key, dimension]) => (
                    <li key={key}>
                      {(
                        {
                          length: "총장",
                          width: "너비",
                          depth: "깊이",
                          sleeve: "소매 길이",
                          waist_width: "허리 단면",
                          hip_width: "골반 단면",
                          rise: "밑위",
                          thigh_width: "바지통 단면",
                          hem_width: "밑단 단면",
                        } as Record<string, string>
                      )[key] ?? key}
                      : {(dimension.value * 100).toFixed(1)} cm ·{" "}
                      {dimension.source === "estimated"
                        ? "추정"
                        : dimension.source === "user_entered"
                          ? "직접 입력"
                          : dimension.source === "ocr"
                            ? "OCR 제안"
                            : dimension.source === "photo_silhouette_estimate"
                              ? "사진 실루엣 기반 추정"
                              : "분석 기반 추정"}
                    </li>
                  ),
                )}
              </ul>
              <p>
                형태:{" "}
                {state.model_metadata.shape_source ===
                "photo_silhouette_estimate"
                  ? "사진의 높이별 외곽 비율 반영"
                  : "일반 템플릿 추정"}{" "}
                · 후면 및 깊이 추정
              </p>
              {state.model_metadata.warnings.map((warning) => (
                <p key={warning}>{warning}</p>
              ))}
            </details>
          ) : null}
        </>
      ) : (
        <p>생성 상태 확인 중…</p>
      )}
      {error ? <p role="alert">{error}</p> : null}
      {pollError ? <p role="alert">{pollError}</p> : null}
    </section>
  );
}
