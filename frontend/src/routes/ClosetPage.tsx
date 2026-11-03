import { useState } from "react";
import { Plus, Search, Trash2 } from "lucide-react";
import { PhotoPreview } from "../components/PhotoPicker";
import { EmptyState, LinkButton, Notice, PageHeading } from "../components/UI";
import { useSession } from "../stores/SessionContext";
import { categories } from "../types/domain";
import type { Category } from "../types/domain";
import { AccountPanel } from "../features/garments/AccountPanel";
import { OutfitLibrary } from "../features/fitting/OutfitLibrary";
import { RecommendationWorkspace } from "../features/recommendations/RecommendationWorkspace";
import { GarmentDetail } from "../features/garments/GarmentDetail";
import { deleteGarment } from "../api/garments";
import type { GarmentDraft } from "../types/domain";

export function ClosetPage() {
  const { garments, setGarments, auth } = useSession();
  const [detail, setDetail] = useState<string>();
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<string>();
  const selected = garments.find((g) => g.id === detail);
  async function remove(item: GarmentDraft) {
    setDeleting(item.id);
    setError("");
    try {
      if (item.source === "server") {
        if (!auth) throw new Error("로그인 후 다시 시도해 주세요.");
        await deleteGarment(auth.token, item.id);
      }
      setGarments((items) => items.filter((g) => g.id !== item.id));
      setMessage(`${item.name} 의류와 관련 이미지를 삭제했습니다.`);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "삭제하지 못했습니다. 다시 시도해 주세요.",
      );
    } finally {
      setDeleting(undefined);
    }
  }
  const [filter, setFilter] = useState<Category | "all">("all");
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState<"garments" | "outfits">("garments");
  const [message, setMessage] = useState("");
  const visible = garments.filter(
    (item) =>
      (filter === "all" || item.category === filter) &&
      item.name.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <>
      <PageHeading
        eyebrow="A WARDROBE THAT KNOWS YOU"
        title="나의 디지털 옷장"
        description="내 옷을 한눈에, 새로운 조합의 가능성을 가까이."
        action={
          <LinkButton to="upload">
            <Plus size={17} />
            의류 추가
          </LinkButton>
        }
      />
      <Notice>
        서버 저장 의류는 로그인한 본인만 불러올 수 있습니다. 탭 초안은
        새로고침하면 사라집니다. 스튜디오에서 저장한 비공개 코디도 불러올 수
        있습니다.
      </Notice>
      <AccountPanel />
      {selected ? (
        <GarmentDetail
          key={selected.id}
          item={selected}
          onClose={() => setDetail(undefined)}
        />
      ) : null}
      {error ? (
        <p role="alert" className="error">
          {error}
        </p>
      ) : null}
      <div className="tabs" role="group" aria-label="보관함 종류">
        <button
          className={tab === "garments" ? "active" : ""}
          onClick={() => setTab("garments")}
        >
          의류 보관함 <span>{garments.length}</span>
        </button>
        <button
          className={tab === "outfits" ? "active" : ""}
          onClick={() => setTab("outfits")}
        >
          코디 보관함 <span>비공개</span>
        </button>
      </div>
      {tab === "garments" ? (
        <>
          <div className="closet-toolbar">
            <div className="filter-chips" role="group" aria-label="의류 분류">
              {(
                [["all", "전체"], ...Object.entries(categories)] as [
                  Category | "all",
                  string,
                ][]
              ).map(([key, label]) => (
                <button
                  key={key}
                  className={filter === key ? "active" : ""}
                  aria-pressed={filter === key}
                  onClick={() => setFilter(key)}
                >
                  {label}
                </button>
              ))}
            </div>
            <label className="search-input">
              <Search size={17} />
              <input
                aria-label="의류 이름 검색"
                placeholder="내 옷 검색"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
          </div>
          {visible.length ? (
            <div className="garment-grid">
              {visible.map((item) => (
                <article className="garment-card" key={item.id}>
                  <div className="garment-photo">
                    <PhotoPreview
                      file={item.cutouts?.front ?? item.photos.front}
                      alt={item.name}
                    />
                    <span className="photo-badge">
                      {item.cutouts?.front
                        ? "배경 제거"
                        : item.photos.front
                          ? "원본 사진"
                          : "사진 비보관"}{" "}
                      ·{" "}
                      {item.model_3d_status === "completed"
                        ? "3D 저장됨"
                        : item.model_3d_status === "queued" ||
                            item.model_3d_status === "processing"
                          ? "3D 생성 중"
                          : "3D 없음"}
                    </span>
                  </div>
                  <div className="garment-info">
                    <small>
                      {categories[item.category]} ·{" "}
                      {item.source === "server" ? "비공개 저장" : "탭 초안"}
                    </small>
                    <h3>{item.name}</h3>
                    <p>
                      {[item.color, item.size, item.material]
                        .filter(Boolean)
                        .join(" · ") || "선택 정보 미입력"}
                    </p>
                    <div className="garment-footer">
                      <time dateTime={item.created_at}>
                        {new Date(item.created_at).toLocaleDateString("ko-KR")}
                      </time>
                      <button
                        type="button"
                        className="button secondary"
                        onClick={() => setDetail(item.id)}
                      >
                        상세 보기 / 수정
                      </button>
                      <button
                        className="icon-button danger"
                        aria-label={`${item.name} 삭제`}
                        disabled={!!deleting}
                        onClick={() => void remove(item)}
                      >
                        <Trash2 size={17} />
                      </button>
                    </div>
                  </div>
                  {item.source === "server" ? (
                    <button
                      type="button"
                      className="button secondary"
                      onClick={() => setDetail(item.id)}
                    >
                      3D 복원
                    </button>
                  ) : null}
                </article>
              ))}
            </div>
          ) : (
            <section className="panel">
              <EmptyState
                title={
                  garments.length
                    ? "조건에 맞는 옷이 없어요"
                    : "첫 번째 옷을 추가해 보세요"
                }
                action={
                  <LinkButton to="upload" secondary>
                    의류 사진 추가
                  </LinkButton>
                }
              >
                {garments.length
                  ? "검색어나 분류를 바꿔 보세요."
                  : "좋아하는 옷 한 벌에서 나만의 스타일 공간이 시작됩니다."}
              </EmptyState>
            </section>
          )}
        </>
      ) : (
        <>
          <OutfitLibrary key={auth?.user.id ?? "guest"} />
          {auth ? (
            <RecommendationWorkspace
              key={auth.token}
              token={auth.token}
              savedOnly
            />
          ) : null}
        </>
      )}
      {message ? (
        <p role="status" className="success">
          {message}
        </p>
      ) : null}
    </>
  );
}
