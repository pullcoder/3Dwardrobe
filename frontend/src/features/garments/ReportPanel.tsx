import { useState } from "react";
import { getReports, reportIssue } from "../../api/garments";
import { Panel } from "../../components/UI";
import { useSession } from "../../stores/SessionContext";

export function ReportPanel() {
  const { auth } = useSession();
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await task();
    } catch (e) {
      setError(e instanceof Error ? e.message : "접수하지 못했습니다.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <Panel
      title="권리 침해 및 분석 결과 신고"
      subtitle="서버에 실제로 접수하며 관리자가 검토 상태를 갱신할 수 있습니다. 로컬 개발용이며 출시 전 외부 권리자의 공개 연락 경로를 추가해야 합니다."
    >
      {!auth ? (
        <p className="helper">
          접수 및 상태 확인에는 로컬 계정 로그인이 필요합니다.
        </p>
      ) : (
        <>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void run(async () => {
                const r = await reportIssue(auth.token, reason);
                setMessage(`접수 번호 ${r.id} · ${r.status}`);
                setReason("");
              });
            }}
          >
            <label className="field">
              신고 내용
              <textarea
                required
                minLength={5}
                maxLength={2000}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </label>
            <button className="button secondary" disabled={busy}>
              신고 접수
            </button>
          </form>
          <button
            className="button secondary"
            disabled={busy}
            onClick={() =>
              void run(async () => {
                const reports = await getReports(auth.token);
                setMessage(
                  reports.map((r) => `${r.id}: ${r.status}`).join(" / ") ||
                    "접수한 신고가 없습니다.",
                );
              })
            }
          >
            내 신고 처리 상태 확인
          </button>
        </>
      )}
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
