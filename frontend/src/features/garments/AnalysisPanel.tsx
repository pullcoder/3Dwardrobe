import { useState } from "react";
import { classify, recognize, segment } from "../../api/garments";
import { PhotoPreview } from "../../components/PhotoPicker";
import { Panel } from "../../components/UI";
import type { Photos } from "../../types/domain";
import type { Analysis, GarmentInfo } from "./types";

export function AnalysisPanel({
  token,
  photos,
  onResult,
  onBusy,
  disabled = false,
}: {
  token?: string;
  photos: Photos;
  onResult: (
    analysis: Analysis,
    cutouts: Partial<Record<"front" | "back", File>>,
    patch: Partial<GarmentInfo>,
  ) => void;
  onBusy: (busy: boolean) => void;
  disabled?: boolean;
}) {
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [errors, setErrors] = useState<string[]>([]);
  const [analysis, setAnalysis] = useState<Analysis>({});
  const [cutouts, setCutouts] = useState<
    Partial<Record<"front" | "back", File>>
  >({});
  const [points, setPoints] = useState({
    front: { x: 50, y: 50 },
    back: { x: 50, y: 50 },
  });
  const enabled = !!token && !!photos.front && consent && !busy && !disabled;
  async function run(only?: "front" | "back") {
    if (!enabled || !token) return;
    setBusy(true);
    onBusy(true);
    setErrors([]);
    const next: Analysis = {
      ...analysis,
      segmentation: { ...analysis.segmentation },
    };
    const files = { ...cutouts };
    const patch: Partial<GarmentInfo> = {};
    const failures: string[] = [];
    async function step(label: string, task: () => Promise<void>) {
      setProgress(label);
      try {
        await task();
      } catch (e) {
        failures.push(
          `${label}: ${e instanceof Error ? e.message : "처리 실패"}`,
        );
        setErrors([...failures]);
      }
    }
    try {
      for (const slot of ["front", "back"] as const) {
        const file = photos[slot];
        if (!file || (only && only !== slot)) continue;
        const label = slot === "front" ? "앞면" : "뒷면";
        if (!only)
          await step(`${label} 의류 분류 중`, async () => {
            const result = await classify(token, file);
            next[slot] = result;
            if (slot === "front")
              Object.assign(patch, {
                garment_type: result.garment_type,
                category: result.category ?? undefined,
                color:
                  result.primary_color === "unknown"
                    ? ""
                    : result.primary_color,
                pattern: result.pattern,
                sleeve: result.sleeve,
                neckline: result.neckline,
              });
          });
        await step(`${label} 배경 제거 중`, async () => {
          const result = await segment(
            token,
            file,
            points[slot].x / 100,
            points[slot].y / 100,
          );
          files[slot] = result.file;
          next.segmentation![slot] = {
            model: result.model,
            predicted_iou: result.predicted_iou,
          };
        });
      }
      if (!only)
        for (const kind of ["size", "material"] as const) {
          const file = photos[kind];
          if (!file) continue;
          await step(
            `${kind === "size" ? "사이즈표" : "소재표"} OCR 중`,
            async () => {
              const result = await recognize(token, file, kind);
              next[kind] = result;
              if (kind === "size") {
                patch.measurements = result.measurements;
                patch.size = result.sizes.join(", ");
              } else {
                patch.composition = result.composition;
                patch.material =
                  result.composition
                    .map(
                      (c) =>
                        `${c.name}${c.percent === null ? "" : ` ${c.percent}%`}`,
                    )
                    .join(", ") || "미확인";
              }
            },
          );
        }
      next.processing_status = failures.length ? "partial" : "completed";
      next.errors = failures;
      setAnalysis(next);
      setCutouts(files);
      onResult(next, files, patch);
      setProgress(
        failures.length
          ? "일부 분석에 실패했습니다. 성공한 결과를 확인하고 재시도할 수 있어요."
          : "분석 처리가 끝났습니다. 원본과 결과를 확인하고 정보를 수정해 주세요.",
      );
    } finally {
      setBusy(false);
      onBusy(false);
    }
  }
  return (
    <Panel
      title="02. AI 분석"
      subtitle="사진을 이 컴퓨터의 로컬 서버로 전송해 CPU로 분석합니다. 분석 중 사진은 메모리에서 처리하며 저장 버튼을 누르기 전에는 DB에 남기지 않습니다."
    >
      <p className="helper">
        앞면에는 중앙에 옷 한 벌만 배치해 주세요. 착용 사진에서는 사람까지
        분리될 수 있어 단독 의류 사진을 권장합니다. 최초 분석은 모델 로딩으로
        오래 걸릴 수 있어요.
      </p>
      {!token ? (
        <p className="helper">
          로컬 계정에 로그인하면 AI 분석과 비공개 옷장 저장을 사용할 수
          있습니다.
        </p>
      ) : null}
      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={consent}
          disabled={busy || disabled}
          onChange={(e) => setConsent(e.target.checked)}
        />
        선택한 의류·라벨 사진을 로컬 서버로 보내 분석합니다. 외부 AI API로
        전송하지 않습니다.
      </label>
      <button
        type="button"
        className="button primary"
        disabled={!enabled}
        onClick={() => void run()}
      >
        {busy ? "분석 처리 중…" : "AI 분석 시작 / 재시도"}
      </button>
      {progress ? (
        <p role="status" className="helper" aria-live="polite">
          {progress} 완료율은 제공하지 않습니다.
        </p>
      ) : null}
      {errors.length ? (
        <div role="alert" className="error">
          {errors.map((e) => (
            <p key={e}>{e}</p>
          ))}
        </div>
      ) : null}
      {(["front", "back"] as const).map((slot) =>
        photos[slot] ? (
          <div key={slot} className="analysis-comparison">
            <h3>{slot === "front" ? "앞면" : "뒷면"} 원본 / 배경 제거</h3>
            <div className="comparison-grid">
              <figure>
                <PhotoPreview file={photos[slot]!} alt={`${slot} 원본 비교`} />
                <figcaption>원본</figcaption>
              </figure>
              <figure className="transparency-grid">
                {cutouts[slot] ? (
                  <PhotoPreview
                    file={cutouts[slot]}
                    alt={`${slot} 투명 배경 결과`}
                  />
                ) : (
                  <p>배경 제거 결과가 아직 없습니다.</p>
                )}
                <figcaption>투명 PNG · 최대 1600px</figcaption>
              </figure>
            </div>
            <p className="helper">
              정확한 의류 윤곽을 보장하지 않습니다. 잘못 분리되면 원본에서 옷
              중앙의 가로·세로 위치를 지정해 재시도하세요.
            </p>
            <div className="action-row">
              {(["x", "y"] as const).map((axis) => (
                <label className="field" key={axis}>
                  {slot === "front" ? "앞면" : "뒷면"}{" "}
                  {axis === "x" ? "가로" : "세로"} 위치 (%)
                  <input
                    type="number"
                    min={0}
                    max={100}
                    step={1}
                    disabled={busy}
                    value={points[slot][axis]}
                    onChange={(e) =>
                      setPoints({
                        ...points,
                        [slot]: {
                          ...points[slot],
                          [axis]: Math.max(
                            0,
                            Math.min(100, Number(e.target.value)),
                          ),
                        },
                      })
                    }
                  />
                </label>
              ))}
              <button
                type="button"
                className="button secondary"
                disabled={!enabled}
                onClick={() => void run(slot)}
              >
                {slot === "front" ? "앞면" : "뒷면"} 배경 제거 재시도
              </button>
            </div>
          </div>
        ) : null,
      )}
      {analysis.front ? (
        <div className="analysis-card">
          <h3>자동 분류 제안</h3>
          <p>
            {analysis.front.garment_type === "unknown"
              ? "의류 종류 미확인"
              : analysis.front.garment_type}{" "}
            · {analysis.front.primary_color}
          </p>
          <p className="helper">
            CLIP 유사도는 정확도·신뢰도 확률이 아닙니다. 핏·보조색·소재·세부
            부자재는 확정하지 않습니다.
          </p>
          <details>
            <summary>구조화된 원본 분석 JSON</summary>
            <pre>{JSON.stringify(analysis, null, 2)}</pre>
          </details>
        </div>
      ) : null}
      {(["size", "material"] as const).map((kind) =>
        analysis[kind] ? (
          <div className="analysis-card" key={kind}>
            <h3>{kind === "size" ? "사이즈표" : "소재표"} OCR 원문</h3>
            <pre>{analysis[kind].text || "인식된 글자 없음"}</pre>
            <p className="helper">
              OCR 엔진 출력 점수: {analysis[kind].confidence} / 100 · 치수
              의미가 맞다는 보장은 아닙니다.
            </p>
            {analysis[kind].warnings.map((w) => (
              <p className="helper" key={w}>
                {w}
              </p>
            ))}
          </div>
        ) : null,
      )}
    </Panel>
  );
}
