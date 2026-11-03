import { useEffect, useState } from "react";
import { recommendationPreview } from "../../api/recommendations";
import type { Recommendation } from "./types";
import "./recommendations.css";

function Preview({
  token,
  id,
  part,
  name,
}: {
  token: string;
  id: string;
  part: string;
  name: string;
}) {
  const [url, setUrl] = useState("");
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl = "";
    void recommendationPreview(token, id, part, controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [token, id, part]);
  return url ? (
    <img src={url} alt={name} />
  ) : (
    <span className="recommend-no-image">
      {failed
        ? "보관 이미지가 없거나 불러올 수 없습니다"
        : "이미지 불러오는 중…"}
    </span>
  );
}

export function RecommendationCards({
  items,
  token,
  busy,
  onSave,
  onFeedback,
  onDelete,
  onTryOn,
}: {
  items: Recommendation[];
  token: string;
  busy: boolean;
  onSave: (item: Recommendation) => void;
  onFeedback: (item: Recommendation, value: Recommendation["feedback"]) => void;
  onDelete: (item: Recommendation) => void;
  onTryOn: (item: Recommendation) => void;
}) {
  return (
    <div className="recommend-grid">
      {items.map((item) => (
        <article
          className="panel recommend-card"
          key={item.id}
          aria-label={item.name}
        >
          <div className="recommend-preview">
            {item.items.map((garment) => (
              <figure key={garment.id}>
                <Preview
                  key={`${token}:${item.id}:${garment.id}`}
                  token={token}
                  id={item.id}
                  part={garment.part}
                  name={garment.name}
                />
                <figcaption>
                  {garment.name} · {garment.reconstruction_mode} 모드
                </figcaption>
              </figure>
            ))}
          </div>
          <small>의류 이미지 조합 · 비공개 · 규칙 기반 추천</small>
          <h3>{item.name}</h3>
          {item.reasons.map((reason) => (
            <p key={reason}>{reason}</p>
          ))}
          {item.notes.length ? (
            <details>
              <summary>치수 참고 정보</summary>
              {item.notes.map((note) => (
                <p key={note}>{note}</p>
              ))}
            </details>
          ) : null}
          {item.warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
          {!item.available ? (
            <p>사용할 수 없는 의류가 포함되었습니다. 다시 추천해 주세요.</p>
          ) : null}
          {!item.fitting_available ? (
            <p>
              3D 입어보기에 필요한 모델이 없습니다.{" "}
              <a href="#/closet">옷장에서 4단계 3D 복원 확인</a>
            </p>
          ) : null}
          <div className="recommend-actions">
            <button
              className="button primary"
              disabled={busy || !item.fitting_available}
              onClick={() => onTryOn(item)}
            >
              3D 입어보기
            </button>
            <button
              className="button secondary"
              disabled={busy || !item.available || !!item.saved_at}
              onClick={() => onSave(item)}
            >
              {item.saved_at ? "저장됨" : "추천 코디 저장"}
            </button>
            {(
              [
                ["like", "마음에 들어요"],
                ["dislike", "별로예요"],
                ["exclude", "추천에서 제외"],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                className="button secondary"
                aria-pressed={item.feedback === value}
                disabled={busy}
                onClick={() =>
                  onFeedback(item, item.feedback === value ? "none" : value)
                }
              >
                {label}
              </button>
            ))}
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => onDelete(item)}
            >
              추천 기록 삭제
            </button>
          </div>
        </article>
      ))}
    </div>
  );
}
