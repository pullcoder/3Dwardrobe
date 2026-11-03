import { useEffect, useRef, useState } from "react";
import {
  Box,
  ChevronRight,
  CircleUserRound,
  Fingerprint,
  Grid2X2,
  Layers,
  LayoutDashboard,
  Menu,
  Settings,
  Shirt,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import type { Route } from "./types/domain";
import { Dashboard } from "./routes/Dashboard";
import { BodyPage } from "./routes/BodyPage";
import { UploadPage } from "./routes/UploadPage";
import { ClosetPage } from "./routes/ClosetPage";
import { StudioPage } from "./routes/StudioPage";
import { RecommendPage } from "./routes/RecommendPage";
import { SettingsPage } from "./routes/SettingsPage";
import { SessionProvider } from "./stores/SessionContext";

const navigation = [
  { key: "home", label: "대시보드", icon: LayoutDashboard },
  { key: "body", label: "내 체형 분석", icon: Fingerprint },
  { key: "mannequin", label: "3D 마네킹", icon: CircleUserRound },
  { key: "upload", label: "의류 등록", icon: Upload },
  { key: "studio", label: "피팅 스튜디오", icon: Box },
  { key: "recommend", label: "AI 코디 추천", icon: Sparkles },
  { key: "closet", label: "디지털 옷장", icon: Layers },
  { key: "settings", label: "설정 및 개인정보", icon: Settings },
] as const;

function currentRoute(): Route {
  const hash = window.location.hash.replace("#/", "");
  return navigation.find((item) => item.key === hash)?.key || "home";
}

export default function App() {
  const [route, setRoute] = useState<Route>(currentRoute);
  const [menuOpen, setMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(
    () => window.matchMedia("(max-width: 820px)").matches,
  );
  const mainRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const media = window.matchMedia("(max-width: 820px)");
    const resize = () => setIsMobile(media.matches);
    media.addEventListener("change", resize);
    return () => media.removeEventListener("change", resize);
  }, []);
  useEffect(() => {
    if (!menuOpen) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [menuOpen]);
  useEffect(() => {
    const update = () => {
      setRoute(currentRoute());
      setMenuOpen(false);
      window.scrollTo(0, 0);
      mainRef.current?.focus();
    };
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  useEffect(() => {
    document.title = `${navigation.find((item) => item.key === route)?.label} · StyleFit AI`;
  }, [route]);
  return (
    <SessionProvider>
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          mainRef.current?.focus();
          mainRef.current?.scrollIntoView();
        }}
      >
        본문으로 건너뛰기
      </a>
      {menuOpen ? (
        <button
          className="sidebar-backdrop"
          aria-label="메뉴 닫기"
          onClick={() => setMenuOpen(false)}
        />
      ) : null}
      <aside
        className={`sidebar ${menuOpen ? "open" : ""}`}
        id="main-navigation"
        inert={isMobile && !menuOpen}
      >
        <a className="brand" href="#/home">
          <span className="brand-icon">
            <Shirt size={24} strokeWidth={1.5} />
          </span>
          <span>
            StyleFit<span className="brand-ai">AI</span>
          </span>
        </a>
        <div className="workspace-label">MY STYLE WORKSPACE</div>
        <nav aria-label="주 메뉴">
          {navigation.map(({ key, label, icon: Icon }, index) => (
            <a
              key={key}
              className={`nav-link ${route === key ? "active" : ""} ${index === 7 ? "nav-settings" : ""}`}
              href={`#/${key}`}
              aria-current={route === key ? "page" : undefined}
            >
              <Icon size={19} strokeWidth={1.65} />
              <span>{label}</span>
              {key === "recommend" ? (
                <span className="nav-new" aria-hidden="true">
                  AI
                </span>
              ) : null}
            </a>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="status-dot" /> LOCAL PREVIEW
          <p>나만의 스타일을 준비하는 공간</p>
          <small>5단계 · 개인화 3D 피팅과 비공개 코디</small>
        </div>
        <div className="profile">
          <div className="profile-avatar">S</div>
          <div>
            <strong>나의 스타일 공간</strong>
            <span>비공개 옷장 · 로컬 개발</span>
          </div>
        </div>
      </aside>
      <div className="app-content">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              aria-label={menuOpen ? "메뉴 닫기" : "메뉴 열기"}
              aria-expanded={menuOpen}
              aria-controls="main-navigation"
              onClick={() => setMenuOpen(!menuOpen)}
            >
              {menuOpen ? <X size={23} /> : <Menu size={23} />}
            </button>
            <Grid2X2 size={16} />
            <span>내 스타일 공간</span>
            <ChevronRight size={13} />
            <strong>
              {navigation.find((item) => item.key === route)?.label}
            </strong>
          </div>
          <div className="topbar-right">
            <span className="local-badge">
              <span className="status-dot" />
              개발 미리보기
            </span>
            <a
              className="top-avatar"
              href="#/settings"
              aria-label="개인정보 관리"
            >
              S
            </a>
          </div>
        </header>
        <main id="main-content" ref={mainRef} tabIndex={-1}>
          {route === "home" ? (
            <Dashboard />
          ) : route === "body" ? (
            <BodyPage key="body" />
          ) : route === "mannequin" ? (
            <BodyPage mannequin key="mannequin" />
          ) : route === "upload" ? (
            <UploadPage />
          ) : route === "studio" ? (
            <StudioPage />
          ) : route === "recommend" ? (
            <RecommendPage />
          ) : route === "closet" ? (
            <ClosetPage />
          ) : (
            <SettingsPage />
          )}
          <footer className="footer">
            <span>
              StyleFit AI <span className="footer-dot">·</span> A little more
              you.
            </span>
            <span>로컬 개발 버전 · 업로드 사진은 기본 비공개</span>
          </footer>
        </main>
      </div>
    </SessionProvider>
  );
}
