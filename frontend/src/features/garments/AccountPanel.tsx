import { useState } from "react";
import {
  authenticate,
  loadWardrobe,
  logout,
  removeAccount,
} from "../../api/garments";
import { Panel } from "../../components/UI";
import { useSession } from "../../stores/SessionContext";

export function AccountPanel() {
  const { auth, setAuth, setGarments, clearSession } = useSession();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [confirm, setConfirm] = useState(false);
  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await action();
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "연결하지 못했습니다. 다시 시도해 주세요.",
      );
    } finally {
      setBusy(false);
      setPassword("");
    }
  }
  return (
    <Panel
      title="비공개 옷장 계정"
      subtitle="로컬 개발 계정입니다. 로그인 정보는 이 탭 메모리에만 유지하며, 저장한 의류는 서버 DB에 남습니다."
    >
      {auth ? (
        <>
          <p>
            <strong>{auth.user.username}</strong> 계정 · 본인 의류만 열람할 수
            있어요.
          </p>
          <div className="action-row">
            <button
              className="button secondary"
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  setGarments(await loadWardrobe(auth.token));
                  setMessage("저장된 의류를 불러왔습니다.");
                })
              }
            >
              저장된 옷장 불러오기
            </button>
            <button
              className="button secondary"
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  await logout(auth.token);
                  setAuth(null);
                  clearSession();
                })
              }
            >
              로그아웃
            </button>
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => setConfirm(!confirm)}
            >
              계정 및 데이터 삭제
            </button>
          </div>
          {confirm ? (
            <form
              className="confirm-box"
              onSubmit={(e) => {
                e.preventDefault();
                void run(async () => {
                  await removeAccount(auth.token, auth.user.username, password);
                  setAuth(null);
                  clearSession();
                  setConfirm(false);
                  setMessage("계정·의류·사진·신고 데이터를 삭제했습니다.");
                });
              }}
            >
              <label className="field">
                계정 삭제 확인 암호
                <input
                  type="password"
                  value={password}
                  required
                  minLength={12}
                  autoComplete="current-password"
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              <button className="button danger-button" disabled={busy}>
                계정 영구 삭제 확인
              </button>
            </form>
          ) : null}
        </>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void run(async () => {
              const session = await authenticate(mode, username, password);
              setGarments([]);
              setAuth(session);
              setMessage(
                "로그인했습니다. 저장된 옷장은 불러오기 버튼으로 확인하세요.",
              );
            });
          }}
        >
          <div className="form-grid three-col">
            <label className="field">
              계정명
              <input
                required
                minLength={3}
                maxLength={40}
                pattern="[a-zA-Z0-9_\-]+"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="영문·숫자·_·-"
              />
            </label>
            <label className="field">
              암호
              <input
                required
                type="password"
                minLength={12}
                maxLength={128}
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="12자 이상"
              />
            </label>
            <label className="field">
              계정 작업
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as typeof mode)}
              >
                <option value="login">로그인</option>
                <option value="register">새 계정 만들기</option>
              </select>
            </label>
          </div>
          <button className="button secondary" disabled={busy}>
            {busy
              ? "계정 확인 중…"
              : mode === "login"
                ? "로그인"
                : "계정 만들기"}
          </button>
        </form>
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
