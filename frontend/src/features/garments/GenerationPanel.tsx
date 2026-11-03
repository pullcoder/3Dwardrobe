import { lazy, Suspense, useEffect, useState } from "react";
import {
  confirmPhotoRights,
  deleteModel,
  generateModel,
  getGeneration,
  getModel,
  withdrawRights,
} from "../../api/garments";
import type { GenerationState, RightStatus } from "./types";
import { useSession } from "../../stores/SessionContext";

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
  const [busy, setBusy] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const result = await getGeneration(token, id, controller.signal);
        if (!controller.signal.aborted) {
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
          setError(
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
        권한이 검증된 원본 디자인의 고정밀 복원.
      </p>
      <p className="helper">
        A도 적법한 입력·처리 권한이 필요하며 모든 디자인의 법적 안전성을
        보장하지 않습니다. 사진 텍스처·로고·일러스트는 복사하지 않습니다. 저장된
        분석/수정 정보를 사용하므로 변경한 정보는 먼저 저장하세요.
      </p>
      {state ? (
        <>
          <p>
            사진 권한: {rightsText[state.photo_rights_status]} · 디자인 복원:{" "}
            {rightsText[state.detailed_rights_status]} · 결과 저장·이용:{" "}
            {rightsText[state.output_rights_status]}
          </p>
          <p>자동 선택 모드: {state.selected_mode ?? "권한 확인 후 결정"}</p>
          <p role="status">
            작업 상태: {states[state.generation_status]}
            {state.generation_status === "processing"
              ? ` · ${state.stage === "mesh" ? "메시·재질 생성" : "GLB 검증"}`
              : ""}
          </p>
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
              B모드는 권한이 검증되었지만 복원 기술 검증이 끝나지 않아
              비활성화되어 있습니다.
            </p>
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
              onClick={() => void act(() => generateModel(token, id))}
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
                  : "정보·권한 변경 또는 삭제 요청으로 이전 작업과 모델이 무효화되었습니다."}
            </p>
          ) : null}
          {bytes && state.model_ready ? (
            <Suspense fallback={<p>3D 뷰어 준비 중…</p>}>
              <GarmentModelViewer key={jobId} bytes={bytes} />
            </Suspense>
          ) : null}
          {state.model_metadata ? (
            <details>
              <summary>모델 정보와 추정 치수</summary>
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
                        } as Record<string, string>
                      )[key] ?? key}
                      : {(dimension.value * 100).toFixed(1)} cm ·{" "}
                      {dimension.source === "estimated"
                        ? "추정"
                        : dimension.source === "user_entered"
                          ? "직접 입력"
                          : dimension.source === "ocr"
                            ? "OCR 제안"
                            : "분석 기반 추정"}
                    </li>
                  ),
                )}
              </ul>
            </details>
          ) : null}
        </>
      ) : (
        <p>생성 상태 확인 중…</p>
      )}
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
