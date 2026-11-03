import {
  ArrowRight,
  ArrowUpRight,
  Box,
  Fingerprint,
  Layers,
  Plus,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { FashionArt } from "../components/FashionArt";
import { EmptyState, LinkButton, PageHeading } from "../components/UI";
import { PhotoPreview } from "../components/PhotoPicker";
import { useSession } from "../stores/SessionContext";
import { categories } from "../types/domain";

const steps = [
  {
    number: "01",
    title: "나를 이해하는 첫 단계",
    text: "사진 또는 직접 입력으로 체형을 준비해요.",
    icon: Fingerprint,
    link: "body",
    label: "내 체형 입력",
  },
  {
    number: "02",
    title: "내 옷에 새로운 가능성을",
    text: "옷 사진을 고르고 정보를 정리해 보세요.",
    icon: Layers,
    link: "upload",
    label: "의류 추가",
  },
  {
    number: "03",
    title: "나만의 피팅 스튜디오",
    text: "마네킹에 의류를 시각적으로 배치해 보세요.",
    icon: Box,
    link: "studio",
    label: "스튜디오 둘러보기",
  },
];

export function Dashboard() {
  const { garments } = useSession();
  return (
    <>
      <PageHeading
        eyebrow="YOUR PERSONAL STYLE SPACE"
        title="오늘의 스타일, 나답게."
        description="내 체형과 내 옷에서 시작하는 새로운 스타일의 가능성."
        action={
          <div className="heading-actions">
            <LinkButton to="recommend">
              <Sparkles size={16} />
              AI 코디 추천
            </LinkButton>
            <LinkButton to="upload" secondary>
              <Plus size={17} />
              의류 추가
            </LinkButton>
          </div>
        }
      />
      <section className="hero-card">
        <div className="hero-copy">
          <span className="pill">
            <Sparkles size={14} /> A LITTLE MORE YOU
          </span>
          <h2>
            입어보기 전에,
            <br />
            나를 먼저 이해하는
            <br />
            <span>스타일의 시작.</span>
          </h2>
          <p>
            내 체형을 준비하고 옷을 모아 보세요.
            <br />
            나만의 디지털 스타일 공간을 함께 만들어가요.
          </p>
          <div className="hero-actions">
            <LinkButton to="body">내 체형부터 시작하기</LinkButton>
            <a className="text-link" href="#/studio">
              스튜디오 보기 <ArrowRight size={17} />
            </a>
          </div>
          <span className="hero-disclaimer">
            6단계 · 내 옷장 기반 규칙 추천·시각적 피팅·비공개 코디
          </span>
        </div>
        <div className="hero-art">
          <div className="art-orbit" />
          <span className="art-caption top">
            <span className="dot" /> PERSONAL WARDROBE
          </span>
          <FashionArt />
          <div className="art-caption bottom">
            <span className="art-swatch" />
            <div>
              <strong>Everyday, reimagined.</strong>
              <small>스타일 컨셉 일러스트</small>
            </div>
            <ArrowUpRight size={19} />
          </div>
        </div>
      </section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">GET STARTED</p>
          <h2>나만의 스타일을 준비하는 방법</h2>
        </div>
        <span className="muted">차근차근, 나에게 맞게</span>
      </div>
      <div className="steps-grid">
        {steps.map(({ number, title, text, icon: Icon, link, label }) => (
          <a className="step-card" href={`#/${link}`} key={number}>
            <div className="step-top">
              <span className="step-icon">
                <Icon size={23} strokeWidth={1.5} />
              </span>
              <span>{number}</span>
            </div>
            <h3>{title}</h3>
            <p>{text}</p>
            <div className="step-link">
              {label}
              <ArrowUpRight size={17} />
            </div>
          </a>
        ))}
      </div>
      <div className="dashboard-bottom">
        <section className="panel">
          <div className="section-heading compact">
            <div>
              <p className="eyebrow">MY WARDROBE</p>
              <h2>
                이번 세션의 의류 초안{" "}
                <span className="count">{garments.length}</span>
              </h2>
            </div>
            <a className="text-link" href="#/closet">
              모두 보기 <ArrowRight size={15} />
            </a>
          </div>
          {garments.length ? (
            <div className="mini-garments">
              {garments.slice(-3).map((item) => (
                <a href="#/closet" key={item.id}>
                  <PhotoPreview file={item.photos.front} alt={item.name} />
                  <strong>{item.name}</strong>
                  <small>{categories[item.category]} · 직접 입력</small>
                </a>
              ))}
            </div>
          ) : (
            <EmptyState title="내 옷으로 채울 첫 번째 공간">
              사진을 추가해 의류 초안을 만들어 보세요.
              <br />
              아직 서버에는 저장되지 않습니다.
            </EmptyState>
          )}
        </section>
        <aside className="privacy-card">
          <ShieldCheck size={28} strokeWidth={1.3} />
          <p className="eyebrow">PRIVATE BY DESIGN</p>
          <h2>
            나의 사진은,
            <br />
            나만의 공간에.
          </h2>
          <p>
            사진은 이 탭의 메모리에서만 유지해요. 외부 AI로 전송하거나 학습에
            사용하지 않아요.
          </p>
          <a className="text-link" href="#/settings">
            데이터 관리하기 <ArrowUpRight size={16} />
          </a>
        </aside>
      </div>
    </>
  );
}
