import { useState } from "react";
import {
  CheckCircle2,
  Circle,
  Server,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { getHealth } from "../api/client";
import { PageHeading, Panel } from "../components/UI";
import { useSession } from "../stores/SessionContext";
import { AccountPanel } from "../features/garments/AccountPanel";
import { ReportPanel } from "../features/garments/ReportPanel";

export function SettingsPage() {
  const { clearSession, garments, bodyPhoto } = useSession();
  const [confirm, setConfirm] = useState(false);
  const [message, setMessage] = useState("");
  const [apiStatus, setApiStatus] = useState("연결 확인 전");
  const [checking, setChecking] = useState(false);
  async function checkApi() {
    setChecking(true);
    try {
      const health = await getHealth();
      setApiStatus(
        health.mode === "local_preview" &&
          !health.features.ai &&
          !health.features.storage
          ? "로컬 API 연결됨 · AI/영구 저장 미연결"
          : "로컬 API 연결됨 · 인증/비공개 저장 사용 가능 · AI 준비 상태는 의류 분석에서 확인하세요.",
      );
    } catch {
      setApiStatus("로컬 API에 연결할 수 없습니다. 백엔드를 실행해 주세요.");
    } finally {
      setChecking(false);
    }
  }
  return (
    <>
      <PageHeading
        eyebrow="YOUR DATA, YOUR CONTROL"
        title="설정 및 개인정보 관리"
        description="어떤 정보가 어디에 있는지, 명확하게 확인하고 관리하세요."
      />
      <AccountPanel />
      <ReportPanel />
      <div className="settings-grid">
        <Panel
          title="현재 데이터 처리"
          subtitle="로컬 개발 미리보기의 실제 동작입니다."
        >
          <ul className="privacy-list">
            <li>
              <CheckCircle2 />
              <div>
                <strong>기본은 탭 메모리, 체형은 선택 저장</strong>
                <p>
                  저장 전 사진·의류 초안은 메모리에서 유지합니다. 의류 저장
                  버튼을 누르면 로컬 서버 DB에 보관합니다. 체형은 명시적으로
                  선택하면 이 기기에 암호화 저장합니다.
                </p>
              </div>
            </li>
            <li>
              <ShieldCheck />
              <div>
                <strong>외부 AI 전송 및 학습 없음</strong>
                <p>
                  MediaPipe는 브라우저 안에서 실행합니다. 신체 사진을 서버에
                  전송하거나 학습에 사용하지 않습니다.
                </p>
              </div>
            </li>
            <li>
              <Server />
              <div>
                <strong>사용자 선택에 따른 로컬 의류 AI</strong>
                <p>
                  의류 분류·배경 제거·OCR은 로컬 CPU에서 처리합니다. 외부 AI
                  전송은 없으며, 저장 전 분석 사진은 디스크에 쓰지 않습니다.
                </p>
              </div>
            </li>
            <li>
              <Circle />
              <div>
                <strong>비공개 계정·신고·삭제</strong>
                <p>
                  로그인 후 본인 의류만 열람합니다. 신고 상태 조회와 계정·관련
                  데이터 삭제를 제공합니다. 인터넷 서비스 운영용은 아닙니다.
                </p>
              </div>
            </li>
          </ul>
        </Panel>
        <Panel
          title="세션 데이터 초기화"
          subtitle={`의류 초안 ${garments.length}개 · 전신 사진 ${bodyPhoto ? "선택됨" : "없음"}`}
        >
          <p className="description">
            이 탭에 입력한 신체 치수와 사진, 의류 초안을 모두 제거합니다. 이
            기기의 암호화 보관함은 체형 화면에서 별도로 삭제해 주세요. 서버 저장
            데이터는 계정 삭제 또는 옷장에서 별도로 삭제해 주세요.
          </p>
          {confirm ? (
            <div className="confirm-box">
              <p>현재 세션 데이터를 모두 제거할까요?</p>
              <div className="action-row">
                <button
                  className="button danger-button"
                  onClick={() => {
                    clearSession();
                    setConfirm(false);
                    setMessage("사진·치수·의류 초안을 초기화했습니다.");
                  }}
                >
                  모두 초기화
                </button>
                <button
                  className="button secondary"
                  onClick={() => setConfirm(false)}
                >
                  취소
                </button>
              </div>
            </div>
          ) : (
            <button
              className="button secondary danger"
              onClick={() => setConfirm(true)}
            >
              <Trash2 size={17} />
              세션 데이터 초기화
            </button>
          )}
          {message ? (
            <p className="success" role="status">
              {message}
            </p>
          ) : null}
        </Panel>
        <Panel title="로컬 API 상태">
          <p role="status" className="description">
            {apiStatus}
          </p>
          <button
            className="button secondary"
            disabled={checking}
            onClick={() => void checkApi()}
          >
            {checking ? "연결 확인 중…" : "API 연결 확인"}
          </button>
        </Panel>
        <Panel title="출시 전 제공할 기능">
          <p className="description">
            현재 계정·의류 삭제와 신고 접수는 위에서 사용할 수 있습니다. 출시
            전에는 외부 웹 삭제 요청, 공개 권리자 연락처, 유해 콘텐츠 검사와
            운영 관리자 인증을 추가해야 합니다.
          </p>
        </Panel>
      </div>
      <Panel title="개발 미리보기 개인정보 안내">
        <p className="description">
          추천은 저장한 취향·본인 옷장·명시적 피드백을 사용합니다. 체형 수치는
          별도 동의 시에만 비교하며 원본 신체 사진을 전송하지 않습니다. 추천
          기록과 치수 차이 설명은 비공개 저장되고, 추천 화면에서 삭제할 수
          있습니다. 계정 삭제 시 취향·추천·피드백도 함께 삭제됩니다. 외부 AI
          학습에 제공하지 않습니다.
        </p>
        <p className="description">
          운영자·연락처·처리 근거·실제 보관 기간을 확정한 출시용
          개인정보처리방침은 아직 제공하지 않습니다. 현재는 로컬에서 사진을 미리
          보고 정보를 준비하는 개발 버전입니다. 외부 AI를 연결하기 전 처리자와
          전송 항목, 보관 기간을 다시 안내합니다.
        </p>
        <p className="helper">
          <a
            className="text-link"
            href="/third-party-notices.txt"
            target="_blank"
            rel="noreferrer"
          >
            오픈소스 라이선스 고지
          </a>
          <br />
          업로드 권리 확인이나 비공개 설정만으로 타인의 저작권·디자인권 문제가
          해결되는 것은 아닙니다.
        </p>
      </Panel>
    </>
  );
}
