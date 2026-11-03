import { useEffect, useRef, useState } from "react";
import { deleteOutfit, getOutfit, getOutfits } from "../../api/fittings";
import { useSession } from "../../stores/SessionContext";
import type {
  FittingState,
  SlotSelection,
  StoredProfile,
} from "../../types/fitting";
import { emptyAdjustments } from "../../types/fitting";
import type { Category, Measurements } from "../../types/domain";
import type { BodyProfile } from "../body/types";

export function restoredProfile(profile: StoredProfile): BodyProfile {
  return {
    values: Object.fromEntries(
      Object.entries(profile.values).map(([k, v]) => [
        k,
        v === null ? "" : String(v),
      ]),
    ) as Measurements,
    origins: profile.origins,
  };
}

export function OutfitLibrary() {
  const alive = useRef(false);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const { auth, setStudio, setBodyMode, setBodyProfiles } = useSession();
  const [items, setItems] = useState<FittingState[]>([]),
    [error, setError] = useState("");
  const [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  useEffect(() => {
    let cancelled = false;
    if (auth)
      void getOutfits(auth.token)
        .then((next) => {
          if (!cancelled) setItems(next);
        })
        .catch((e) => {
          if (!cancelled)
            setError(e instanceof Error ? e.message : "코디 조회 실패");
        });
    return () => {
      cancelled = true;
    };
  }, [auth]);
  async function load(id: string) {
    if (!auth) return;
    setBusy(true);
    setError("");
    try {
      const outfit = await getOutfit(auth.token, id);
      if (!alive.current) return;
      if (!outfit.mannequin) throw new Error("저장된 마네킹이 없습니다.");
      const selected: SlotSelection = {},
        pins: Partial<Record<Category, string>> = {};
      for (const part of ["top", "bottom", "outer"] as const) {
        const resource = outfit.slots[part];
        if (resource?.status === "available") {
          selected[part] = resource.garment_id;
          pins[part] = resource.model_asset_id;
        }
      }
      const profile = restoredProfile(outfit.mannequin),
        mode = outfit.mannequin.mode;
      setBodyProfiles((profiles) => ({ ...profiles, [mode]: profile }));
      setBodyMode(mode);
      setStudio({
        owner_id: auth.user.id,
        selected,
        pins,
        adjustments: outfit.adjustments ?? emptyAdjustments(),
        mannequin_id: outfit.mannequin_id ?? undefined,
        warnings: outfit.warnings,
      });
      setMessage(
        outfit.warnings.join(" ") || "저장된 코디와 체형을 복원했습니다.",
      );
      window.location.assign("#/studio");
    } catch (e) {
      setError(e instanceof Error ? e.message : "코디 불러오기 실패");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel" aria-label="저장된 코디">
      <h2>저장된 코디</h2>
      {!auth ? (
        <p>로그인하면 본인의 비공개 코디를 조회할 수 있습니다.</p>
      ) : (
        <>
          <button
            className="button secondary"
            type="button"
            disabled={busy}
            onClick={() => {
              setBusy(true);
              void getOutfits(auth.token)
                .then(setItems)
                .catch((e) =>
                  setError(e instanceof Error ? e.message : "코디 조회 실패"),
                )
                .finally(() => setBusy(false));
            }}
          >
            코디 목록 새로고침
          </button>
          {!items.length ? (
            <p>저장된 코디가 없습니다.</p>
          ) : (
            items.map((item) => (
              <article key={item.id} className="saved-outfit">
                <h3>{item.name}</h3>
                <p>{new Date(item.created_at).toLocaleString()} · 비공개</p>
                {item.warnings.map((warning) => (
                  <p key={warning}>{warning}</p>
                ))}
                <button
                  className="button secondary"
                  type="button"
                  disabled={busy}
                  onClick={() => void load(item.id)}
                >
                  {item.name} 불러오기
                </button>
                <button
                  className="button secondary"
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    setBusy(true);
                    void deleteOutfit(auth.token, item.id)
                      .then(() => {
                        setItems((current) =>
                          current.filter((o) => o.id !== item.id),
                        );
                        setMessage("코디를 삭제했습니다.");
                      })
                      .catch((e) =>
                        setError(
                          e instanceof Error ? e.message : "코디 삭제 실패",
                        ),
                      )
                      .finally(() => setBusy(false));
                  }}
                >
                  {item.name} 코디 삭제
                </button>
              </article>
            ))
          )}
        </>
      )}
      {error ? <p role="alert">{error}</p> : null}
      {message ? <p role="status">{message}</p> : null}
    </section>
  );
}
