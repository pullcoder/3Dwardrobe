import { useState } from "react";
import { reportIssue, updateGarment } from "../../api/garments";
import { PhotoPreview } from "../../components/PhotoPicker";
import { Panel } from "../../components/UI";
import { useSession } from "../../stores/SessionContext";
import type { GarmentDraft } from "../../types/domain";
import { GarmentEditor } from "./GarmentEditor";
import { blankInfo } from "./types";

export function GarmentDetail({
  item,
  onClose,
}: {
  item: GarmentDraft;
  onClose: () => void;
}) {
  const { auth, setGarments } = useSession();
  const [info, setInfo] = useState(
    item.info ?? {
      ...blankInfo,
      name: item.name,
      category: item.category,
      color: item.color,
      size: item.size,
      material: item.material,
    },
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [reason, setReason] = useState("");
  async function save() {
    setBusy(true);
    setError("");
    try {
      let revision = item.revision;
      if (item.source === "server") {
        if (!auth) throw new Error("로그인 후 다시 시도해 주세요.");
        const updated = await updateGarment(
          auth.token,
          item.id,
          info,
          item.revision!,
        );
        revision = updated.revision;
      }
      setGarments((items) =>
        items.map((g) =>
          g.id === item.id ? { ...g, ...info, info, revision } : g,
        ),
      );
      setMessage("의류 정보를 수정했습니다. 원본 분석은 유지됩니다.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "수정에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <Panel
      title={`${item.name} 상세 정보`}
      subtitle="원본 분석과 수정 정보를 확인할 수 있어요."
    >
      <button className="button secondary" type="button" onClick={onClose}>
        상세 닫기
      </button>
      <div className="detail-photos">
        {[
          ...Object.entries(item.photos),
          ...Object.entries(item.cutouts ?? {}).map(
            ([key, file]) => [`cutout_${key}`, file] as const,
          ),
        ].map(([slot, file]) =>
          file ? (
            <figure key={slot}>
              <PhotoPreview file={file} alt={`${item.name} ${slot}`} />
              <figcaption>{slot}</figcaption>
            </figure>
          ) : null,
        )}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <GarmentEditor value={info} onChange={setInfo} disabled={busy} />
        <button className="button primary" disabled={busy || !info.name.trim()}>
          정보 수정 저장
        </button>
      </form>
      <details>
        <summary>저장된 원본 분석 JSON</summary>
        <pre>{JSON.stringify(item.analysis ?? {}, null, 2)}</pre>
      </details>
      <button className="button secondary" disabled>
        3D 모델 생성 · 4단계에서 지원 예정
      </button>
      {auth ? (
        <form
          className="report-form"
          onSubmit={(e) => {
            e.preventDefault();
            setBusy(true);
            setError("");
            void reportIssue(
              auth.token,
              reason,
              item.source === "server" ? item.id : undefined,
            )
              .then((r) => {
                setMessage(`신고 접수 완료 · ${r.id} · ${r.status}`);
                setReason("");
              })
              .catch((e) =>
                setError(
                  e instanceof Error ? e.message : "신고 접수에 실패했습니다.",
                ),
              )
              .finally(() => setBusy(false));
          }}
        >
          <label className="field">
            권리 침해·분석 결과 신고
            <textarea
              value={reason}
              required
              minLength={5}
              maxLength={2000}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
          <button className="button secondary" disabled={busy}>
            신고 접수
          </button>
        </form>
      ) : null}
      {message ? (
        <p role="status" className="success">
          {message}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="error">
          {error}
        </p>
      ) : null}
    </Panel>
  );
}
