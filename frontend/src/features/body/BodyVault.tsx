import { useState } from "react";
import { LockKeyhole, Save, Trash2, UnlockKeyhole } from "lucide-react";
import { useSession } from "../../stores/SessionContext";
import { deleteBodyVault, loadBodyVault, saveBodyVault } from "./vault";

export function BodyVault({
  disabled = false,
  onRestore,
}: {
  disabled?: boolean;
  onRestore?: () => void;
}) {
  const { bodyProfiles, setBodyProfiles, setBodyPhoto } = useSession();
  const [alias, setAlias] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const blocked = busy || disabled;
  async function run(action: "save" | "load" | "delete") {
    if (blocked) return;
    setBusy(true);
    setMessage("");
    setError("");
    try {
      if (action === "save") {
        await saveBodyVault(alias, password, bodyProfiles);
        setMessage(
          "두 체형을 이 기기에 암호화 저장했습니다. 원본 사진·관절 좌표·암호는 저장하지 않았습니다.",
        );
      }
      if (action === "load") {
        const profiles = await loadBodyVault(alias, password);
        onRestore?.();
        setBodyProfiles(profiles);
        setBodyPhoto(undefined);
        setMessage("두 체형을 불러왔습니다. 원본 사진은 보관함에 없습니다.");
      }
      if (action === "delete") {
        await deleteBodyVault(alias, password);
        setMessage(
          "이 기기의 해당 체형 보관함을 삭제했습니다. 현재 편집 중인 체형은 별도로 삭제할 수 있습니다.",
        );
        setConfirmDelete(false);
      }
      setPassword("");
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "기기 저장소를 사용할 수 없습니다.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel body-vault">
      <div className="panel-heading">
        <h2>
          <LockKeyhole size={18} />
          선택: 이 기기에 암호화 저장
        </h2>
        <p>
          사진 분석 체형과 수동 체형을 함께 보관합니다. 서버 계정 저장이 아니며,
          다른 기기와 동기화되지 않습니다.
        </p>
      </div>
      <div className="form-grid">
        <label className="field">
          <span>보관함 이름</span>
          <input
            autoComplete="off"
            maxLength={80}
            value={alias}
            onChange={(e) => setAlias(e.target.value)}
            placeholder="나만의 보관함 이름"
          />
        </label>
        <label className="field">
          <span>보관함 암호 (12자 이상)</span>
          <input
            type="password"
            autoComplete="off"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="암호 분실 시 복구 불가"
          />
        </label>
      </div>
      <div className="action-row">
        <button
          className="button secondary"
          disabled={blocked || !alias.trim() || password.length < 12}
          onClick={() => void run("save")}
        >
          <Save size={16} />이 기기에 저장
        </button>
        <button
          className="button secondary"
          disabled={blocked || !alias.trim() || password.length < 12}
          onClick={() => void run("load")}
        >
          <UnlockKeyhole size={16} />
          보관함 불러오기
        </button>
        <button
          className="button secondary danger"
          disabled={blocked || !alias.trim() || password.length < 12}
          onClick={() => setConfirmDelete(true)}
        >
          <Trash2 size={16} />
          기기 저장 삭제
        </button>
      </div>
      {confirmDelete ? (
        <div className="confirm-box">
          <p>해당 보관함을 이 기기에서 삭제할까요? 되돌릴 수 없습니다.</p>
          <div className="action-row">
            <button
              className="button danger-button"
              disabled={blocked}
              onClick={() => void run("delete")}
            >
              보관함 삭제 확인
            </button>
            <button
              className="button secondary"
              disabled={blocked}
              onClick={() => setConfirmDelete(false)}
            >
              취소
            </button>
          </div>
        </div>
      ) : null}
      {busy ? (
        <p className="helper" role="status">
          체형 보관함을 처리하고 있어요.
        </p>
      ) : null}
      {message ? (
        <p className="success" role="status">
          {message}
        </p>
      ) : null}
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
      <p className="helper">
        AES-GCM 암호화 · 암호는 전송/저장하지 않음. 공용 기기에서는 작업 후
        세션을 초기화하세요. 브라우저 데이터 삭제 시 보관함도 사라집니다. HTTPS
        또는 localhost에서 사용하세요.
      </p>
    </section>
  );
}
