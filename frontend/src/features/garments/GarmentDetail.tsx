import { useState } from "react";
import {
  reportIssue,
  updateGarment,
  requestRightsReview,
  uploadRightsEvidence,
} from "../../api/garments";
import { PhotoPreview } from "../../components/PhotoPicker";
import { Panel } from "../../components/UI";
import { useSession } from "../../stores/SessionContext";
import type { GarmentDraft } from "../../types/domain";
import { GarmentEditor } from "./GarmentEditor";
import { GenerationPanel } from "./GenerationPanel";
import { blankInfo, defaultPolicy, rightsLabels } from "./types";

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
  const [reportKind, setReportKind] = useState<"rights" | "analysis">("rights");
  const [licenseReference, setLicenseReference] = useState("");
  const [evidenceFile, setEvidenceFile] = useState<File>();
  const [evidenceConsent, setEvidenceConsent] = useState(false);
  const policy = item.reconstruction ?? defaultPolicy;
  async function supplementEvidence() {
    if (!auth || !evidenceFile || !evidenceConsent) return;
    setBusy(true);
    setError("");
    try {
      await uploadRightsEvidence(auth.token, item.id, evidenceFile);
      setMessage(
        "추가 증빙을 비공개 제출했습니다. 담당자의 문서 검토가 필요합니다.",
      );
      setEvidenceFile(undefined);
      setEvidenceConsent(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "증빙 제출에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }
  async function submitReview() {
    if (!auth || item.source !== "server" || !item.revision) return;
    setBusy(true);
    setError("");
    try {
      const evidence =
        evidenceFile && evidenceConsent
          ? await uploadRightsEvidence(auth.token, item.id, evidenceFile)
          : undefined;
      const updated = await requestRightsReview(
        auth.token,
        item.id,
        licenseReference,
        item.revision,
        evidence?.id,
      );
      setGarments((items) =>
        items.map((g) =>
          g.id === item.id
            ? {
                ...g,
                revision: updated.revision,
                reconstruction: {
                  ...policy,
                  rights_status: updated.rights_status,
                  license_reference: updated.license_reference,
                  rights_reviewed_at: updated.rights_reviewed_at,
                },
              }
            : g,
        ),
      );
      setMessage(
        "검토 요청을 접수했습니다. 담당자가 증빙의 세 권한을 검증해야 합니다. B는 저장 사진이 있는 바지 앞면 투영에 한해 제공하며 고정밀 복원은 아닙니다.",
      );
      setEvidenceFile(undefined);
      setEvidenceConsent(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "검토 요청에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }
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
      {auth && item.source === "server" ? (
        <GenerationPanel
          key={item.id}
          token={auth.token}
          id={item.id}
          garmentType={item.info?.garment_type ?? "unknown"}
        />
      ) : (
        <p>
          3D 복원을 사용하려면 로그인 후 의류를 비공개 옷장에 저장해 주세요.
        </p>
      )}
      <p>
        복원 모드: {policy.reconstruction_mode} · 권한 상태:{" "}
        {rightsLabels[policy.rights_status]} · 모델 공개 범위: 비공개
      </p>
      <p>
        원본 보관:{" "}
        {policy.original_image_retention === "temporary" ? "임시" : "저장 동의"}{" "}
        · 권한 검토 시각: {policy.rights_reviewed_at ?? "미검토"}
      </p>
      <p className="helper">
        B모드는 사진 처리, 보호되는 그래픽·디자인 복원, 생성 결과 저장·이용의 세
        권한을 증빙으로 검증한 뒤에만 제공할 예정입니다. 담당자가 제출 문서와 세
        권한을 검토합니다. AI 분류나 체크박스는 승인 근거를 대신하지 않습니다.
      </p>
      <button type="button" className="button secondary" disabled>
        B모드 고정밀 복원 · 준비 중
      </button>
      {auth && item.source === "server" ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void submitReview();
          }}
        >
          <label className="field">
            권리 증빙 참조
            <textarea
              value={licenseReference}
              minLength={5}
              maxLength={1000}
              required
              disabled={busy || policy.rights_status === "pending"}
              onChange={(e) => setLicenseReference(e.target.value)}
            />
          </label>
          <p className="helper">
            권리자 이용허락 문서·라이선스의 문서 번호 등 참조를 입력하세요.
            민감한 문서 원문은 입력하지 마세요. 외부 주소를 자동 수집하지
            않습니다.
          </p>
          <label className="field">
            권리 증빙 문서 (선택)
            <input
              type="file"
              style={{
                position: "static",
                opacity: 1,
                height: "auto",
                maxWidth: "100%",
                width: "100%",
                minWidth: 0,
              }}
              accept="application/pdf,image/png,image/jpeg,image/webp"
              disabled={busy}
              onChange={(e) => setEvidenceFile(e.target.files?.[0])}
            />
          </label>
          {policy.rights_status === "pending" ? (
            <button
              type="button"
              className="button secondary"
              disabled={
                busy ||
                !evidenceFile ||
                !evidenceConsent ||
                evidenceFile.size > 5 * 1024 * 1024
              }
              onClick={() => void supplementEvidence()}
            >
              추가 증빙 제출
            </button>
          ) : null}
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={evidenceConsent}
              disabled={busy}
              onChange={(e) => setEvidenceConsent(e.target.checked)}
            />
            선택한 권리 증빙 문서를 비공개 보관하고 담당자가 검토하는 데
            동의합니다.
          </label>
          <p className="helper">
            5 MiB 이하. 필요한 범위 외 개인정보는 가려 주세요. 참조만 제출할
            수도 있지만 실제 문서 없이는 승인되지 않습니다.
          </p>
          {policy.license_reference ? (
            <p>접수된 증빙 참조: {policy.license_reference}</p>
          ) : null}
          <button
            className="button secondary"
            disabled={
              busy ||
              policy.rights_status === "pending" ||
              (!!evidenceFile &&
                (!evidenceConsent || evidenceFile.size > 5 * 1024 * 1024))
            }
          >
            B모드 권한 검토 요청
          </button>
        </form>
      ) : null}
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
              reportKind,
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
          <label className="field">
            신고 종류
            <select
              value={reportKind}
              onChange={(e) =>
                setReportKind(e.target.value as "rights" | "analysis")
              }
            >
              <option value="rights">권리 침해 (생성·모델 이용 중단)</option>
              <option value="analysis">분석 결과 오류</option>
            </select>
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
