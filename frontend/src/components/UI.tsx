import type { ReactNode } from "react";
import { ArrowUpRight, Info, LockKeyhole, Sparkles } from "lucide-react";

export function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="notice">
      <Info size={18} />
      <div>{children}</div>
    </div>
  );
}
export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="description">{description}</p>
      </div>
      {action}
    </div>
  );
}
export function Panel({
  title,
  subtitle,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <h2>{title}</h2>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      {children}
    </section>
  );
}
export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Sparkles size={25} strokeWidth={1.3} />
      </div>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
export function PrivacyNote() {
  return (
    <p className="privacy-note">
      <LockKeyhole size={14} />
      저장 전 사진은 탭 메모리에서 유지 · 서버 저장은 별도 선택 · AI 학습에
      사용하지 않음
    </p>
  );
}
export function ComingButton({ children }: { children: ReactNode }) {
  return (
    <button className="button secondary" disabled>
      {children}
      <span className="tiny-tag">준비 중</span>
    </button>
  );
}
export function LinkButton({
  to,
  children,
  secondary = false,
}: {
  to: string;
  children: ReactNode;
  secondary?: boolean;
}) {
  return (
    <a
      className={`button ${secondary ? "secondary" : "primary"}`}
      href={`#/${to}`}
    >
      {children}
      <ArrowUpRight size={17} />
    </a>
  );
}
