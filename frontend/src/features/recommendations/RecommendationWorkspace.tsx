import { useEffect, useRef, useState } from "react";
import {
  applyRecommendation,
  deleteRecommendation,
  feedbackRecommendation,
  generateRecommendations,
  getPreferences,
  listRecommendations,
  putPreferences,
  saveRecommendation,
} from "../../api/recommendations";
import { loadWardrobe } from "../../api/garments";
import { useSession } from "../../stores/SessionContext";
import { Panel } from "../../components/UI";
import { emptyAdjustments } from "../../types/fitting";
import type { StoredProfile } from "../../types/fitting";
import { validateMeasurements } from "../body/measurements";
import { restoredProfile } from "../fitting/OutfitLibrary";
import { RecommendationCards } from "./RecommendationCards";
import type { Preferences, Recommendation } from "./types";

const styles = {
  minimal: "미니멀",
  casual: "캐주얼",
  street: "스트릿",
  formal: "포멀",
  business_casual: "비즈니스 캐주얼",
  sporty: "스포티",
  vintage: "빈티지",
  other: "기타",
};
const choices = {
  fit: {
    any: "상관없음",
    slim: "슬림핏",
    regular: "레귤러핏",
    oversized: "오버핏",
  },
  purpose: {
    any: "상관없음",
    daily: "일상",
    work: "출근·미팅",
    occasion: "특별한 약속",
    exercise: "운동",
    travel: "여행",
  },
  season: {
    any: "상관없음",
    spring: "봄",
    summer: "여름",
    autumn: "가을",
    winter: "겨울",
  },
  mood: {
    any: "상관없음",
    calm: "차분한",
    neat: "단정한",
    active: "활동적인",
    expressive: "개성 있는",
  },
};

export function RecommendationWorkspace({
  token,
  savedOnly = false,
}: {
  token: string;
  savedOnly?: boolean;
}) {
  const {
    auth,
    bodyMode,
    bodyProfiles,
    studio,
    setStudio,
    setBodyMode,
    setBodyProfiles,
    setGarments,
  } = useSession();
  const [prefs, setPrefs] = useState<Preferences>();
  const [items, setItems] = useState<Recommendation[]>([]);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const [bodyConsent, setBodyConsent] = useState(false),
    [count, setCount] = useState(4);
  const [view, setView] = useState(savedOnly),
    [offset, setOffset] = useState(0);
  const [pending, setPending] = useState<Recommendation>();
  const alive = useRef(false);
  const requestEpoch = useRef(0);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  useEffect(() => {
    let cancelled = false;
    const epoch = ++requestEpoch.current;
    void Promise.all([
      getPreferences(token),
      listRecommendations(token, view, offset),
    ])
      .then(([p, rows]) => {
        if (!cancelled && epoch === requestEpoch.current) {
          setPrefs(p);
          setItems(rows);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled && epoch === requestEpoch.current)
          setError(e instanceof Error ? e.message : "불러오기 실패");
      });
    return () => {
      cancelled = true;
    };
  }, [token, view, offset]);
  async function action(work: () => Promise<void>) {
    requestEpoch.current += 1;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await work();
    } catch (e) {
      if (alive.current)
        setError(
          e instanceof Error ? e.message : "처리 실패. 다시 시도해 주세요.",
        );
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  function replace(row: Recommendation) {
    if (alive.current)
      setItems((current) =>
        current.map((item) => (item.id === row.id ? row : item)),
      );
  }
  async function tryOn(item: Recommendation) {
    if (!auth) return;
    const result = await applyRecommendation(
      token,
      item.id,
      studio.owner_id === auth.user.id ? studio.mannequin_id : undefined,
    );
    const wardrobe = await loadWardrobe(token);
    if (!alive.current) return;
    const currentProfile = bodyProfiles[bodyMode];
    const hasCurrentBody = Object.values(currentProfile.values).some(
      (value) => value.trim() !== "",
    );
    // 탭에서 편집한 체형을 오래된 서버 스냅샷으로 덮어쓰지 않는다.
    const sameBody =
      result.mannequin?.mode === bodyMode &&
      Object.entries(currentProfile.values).every(
        ([key, value]) =>
          (value.trim() === "" ? null : Number(value)) ===
          result.mannequin?.values[key as keyof StoredProfile["values"]],
      );
    if (result.mannequin && !hasCurrentBody) {
      const profile = result.mannequin;
      setBodyProfiles((current) => ({
        ...current,
        [profile.mode]: restoredProfile(profile),
      }));
      setBodyMode(profile.mode);
    }
    setGarments(wardrobe);
    setStudio({
      owner_id: auth.user.id,
      selected: result.slots,
      pins: result.pins,
      adjustments: emptyAdjustments(),
      mannequin_id:
        !hasCurrentBody || sameBody
          ? (result.mannequin_id ?? undefined)
          : undefined,
      recommendation_id: result.recommendation_id,
      warnings: [
        "추천 코디를 장착했습니다. 현재 선택 체형으로 시각적 근사 피팅을 표시합니다.",
      ],
    });
    window.location.assign("#/studio");
  }
  return (
    <>
      {!savedOnly ? (
        <Panel
          title="나의 스타일 취향"
          subtitle="체형 수치 없이도 추천할 수 있습니다. 취향은 추천 실행 시 함께 저장합니다."
        >
          {!prefs ? (
            <button
              className="button secondary"
              disabled={busy}
              onClick={() =>
                void action(async () => {
                  const p = await getPreferences(token);
                  if (alive.current) setPrefs(p);
                })
              }
            >
              취향 다시 불러오기
            </button>
          ) : (
            <>
              <fieldset disabled={busy}>
                <legend>선호 스타일 · 여러 개 선택 가능</legend>
                <div className="recommend-styles">
                  {Object.entries(styles).map(([key, label]) => (
                    <label key={key}>
                      <input
                        type="checkbox"
                        checked={prefs.styles.includes(key)}
                        onChange={(e) =>
                          setPrefs({
                            ...prefs,
                            styles: e.target.checked
                              ? [...prefs.styles, key]
                              : prefs.styles.filter((s) => s !== key),
                          })
                        }
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </fieldset>
              <div className="form-grid three-col">
                {(
                  [
                    ["fit", "선호 핏"],
                    ["purpose", "착용 목적"],
                    ["season", "계절"],
                    ["mood", "코디 분위기"],
                  ] as const
                ).map(([key, label]) => (
                  <label className="field" key={key}>
                    <span>{label}</span>
                    <select
                      aria-label={label}
                      disabled={busy}
                      value={prefs[key]}
                      onChange={(e) =>
                        setPrefs({ ...prefs, [key]: e.target.value })
                      }
                    >
                      {Object.entries(choices[key]).map(([value, name]) => (
                        <option key={value} value={value}>
                          {name}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
                {(
                  [
                    ["preferred_colors", "선호 색상"],
                    ["avoided_colors", "피하고 싶은 색상"],
                    ["preferred_types", "선호 의류 종류"],
                  ] as const
                ).map(([key, label]) => (
                  <label className="field" key={key}>
                    <span>{label} · 쉼표로 구분</span>
                    <input
                      disabled={busy}
                      value={prefs[key].join(",")}
                      onChange={(e) =>
                        setPrefs({ ...prefs, [key]: e.target.value.split(",") })
                      }
                      onBlur={() =>
                        setPrefs({
                          ...prefs,
                          [key]: prefs[key]
                            .map((s) => s.trim())
                            .filter(Boolean),
                        })
                      }
                      maxLength={500}
                    />
                  </label>
                ))}
              </div>
              <button
                className="button secondary"
                disabled={busy}
                onClick={() =>
                  void action(async () => {
                    const next = await putPreferences(token, prefs);
                    if (alive.current) {
                      setPrefs(next);
                      setMessage("취향을 비공개 저장했습니다.");
                    }
                  })
                }
              >
                취향 저장
              </button>
              <button
                className="button secondary"
                disabled={busy}
                onClick={() =>
                  void action(async () => {
                    const next = await getPreferences(token);
                    if (alive.current) {
                      setPrefs(next);
                      setMessage("저장한 취향을 다시 불러왔습니다.");
                    }
                  })
                }
              >
                저장한 취향 다시 불러오기
              </button>
              <label className="field">
                <span>추천 개수</span>
                <select
                  aria-label="추천 개수"
                  value={count}
                  disabled={busy}
                  onChange={(e) => setCount(Number(e.target.value))}
                >
                  {[3, 4, 5].map((n) => (
                    <option key={n}>{n}</option>
                  ))}
                </select>
              </label>
              <label className="recommend-body-consent">
                <input
                  type="checkbox"
                  checked={bodyConsent}
                  disabled={busy}
                  onChange={(e) => setBodyConsent(e.target.checked)}
                />
                현재 선택 체형의 입력·추정 치수를 추천 서버에서 비교하는 데
                동의합니다. 원본 사진과 원시 체형 수치는 저장하지 않으며 치수
                차이 설명은 비공개 추천 기록에 남습니다.
              </label>
              <button
                className="button primary"
                disabled={busy}
                onClick={() =>
                  void action(async () => {
                    if (
                      bodyConsent &&
                      validateMeasurements(bodyProfiles[bodyMode].values)
                    )
                      throw new Error(
                        "내 체형 화면에서 치수 오류를 수정해 주세요.",
                      );
                    const saved = await putPreferences(token, prefs);
                    if (!alive.current) return;
                    setPrefs(saved);
                    const profile = bodyProfiles[bodyMode];
                    const body: StoredProfile | undefined = bodyConsent
                      ? {
                          mode: bodyMode,
                          origins: profile.origins,
                          values: Object.fromEntries(
                            Object.entries(profile.values).map(
                              ([key, value]) => [
                                key,
                                value.trim() === "" ? null : Number(value),
                              ],
                            ),
                          ) as StoredProfile["values"],
                        }
                      : undefined;
                    const result = await generateRecommendations(
                      token,
                      count,
                      body,
                    );
                    if (alive.current) {
                      setItems(result.items);
                      setMessage(
                        result.message +
                          ` ${result.stats.evaluated}개 후보를 비교했습니다.`,
                      );
                    }
                  })
                }
              >
                AI 코디 추천 · 규칙 기반
              </button>
            </>
          )}
        </Panel>
      ) : (
        <h2>저장한 추천 코디</h2>
      )}
      <div className="recommend-actions">
        {!savedOnly ? (
          <button
            className="button secondary"
            disabled={busy}
            onClick={() => {
              setView(!view);
              setOffset(0);
            }}
          >
            {view ? "전체 추천 기록" : "저장한 추천만 보기"}
          </button>
        ) : null}
        <button
          className="button secondary"
          disabled={busy}
          onClick={() =>
            void action(async () => {
              const rows = await listRecommendations(token, view, offset);
              if (alive.current) setItems(rows);
            })
          }
        >
          추천 기록 새로고침
        </button>
        <button
          className="button secondary"
          disabled={busy || offset === 0}
          onClick={() => setOffset(Math.max(0, offset - 30))}
        >
          이전 기록
        </button>
        <button
          className="button secondary"
          disabled={busy || items.length < 30}
          onClick={() => setOffset(offset + 30)}
        >
          다음 기록
        </button>
      </div>
      {busy ? <p role="status">요청을 처리하고 있습니다…</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {message ? <p role="status">{message}</p> : null}
      {pending ? (
        <div
          className="recommend-confirm"
          role="group"
          aria-label="추천 코디로 교체 확인"
        >
          <p>
            기존 스튜디오 코디를 추천 코디로 교체할까요? 기존 코디를 유지하려면
            취소하세요.
          </p>
          <button
            className="button primary"
            disabled={busy}
            onClick={() => {
              const next = pending;
              setPending(undefined);
              void action(() => tryOn(next));
            }}
          >
            추천 코디로 교체
          </button>
          <button
            className="button secondary"
            disabled={busy}
            onClick={() => setPending(undefined)}
          >
            기존 코디 유지
          </button>
        </div>
      ) : null}
      {!items.length && !busy ? (
        <p>
          추천 기록이 없습니다. 저장된 상의와 하의가 필요합니다. 부족하면 가능한
          조합만 제공합니다.
        </p>
      ) : null}
      <RecommendationCards
        token={token}
        items={items}
        busy={busy}
        onSave={(item) =>
          void action(async () => {
            const row = await saveRecommendation(token, item.id);
            replace(row);
            if (alive.current) setMessage("추천 코디를 비공개 저장했습니다.");
          })
        }
        onFeedback={(item, value) =>
          void action(async () => {
            replace(await feedbackRecommendation(token, item.id, value));
            if (alive.current)
              setMessage("피드백을 저장했습니다. 다음 추천부터 반영됩니다.");
          })
        }
        onDelete={(item) =>
          void action(async () => {
            await deleteRecommendation(token, item.id);
            if (alive.current) {
              setItems((current) =>
                current.filter((row) => row.id !== item.id),
              );
              setMessage("추천 기록과 피드백을 삭제했습니다.");
            }
          })
        }
        onTryOn={(item) => {
          if (
            studio.owner_id === auth?.user.id &&
            Object.values(studio.selected).some(Boolean)
          )
            setPending(item);
          else void action(() => tryOn(item));
        }}
      />
    </>
  );
}
