import { request } from "./garments";
import type {
  AppliedRecommendation,
  Preferences,
  Recommendation,
} from "../features/recommendations/types";
import type { StoredProfile } from "../types/fitting";

export async function recommendationPreview(
  token: string,
  id: string,
  part: string,
  signal: AbortSignal,
) {
  return (
    await request(`/recommendations/${id}/preview/${part}`, token, { signal })
  ).blob();
}

async function json<T>(
  token: string,
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  return (
    await request(path, token, {
      method,
      ...(body === undefined
        ? {}
        : {
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }),
    })
  ).json();
}
export const getPreferences = (token: string) =>
  json<Preferences>(token, "/style-preferences");
export const putPreferences = (token: string, prefs: Preferences) =>
  json<Preferences>(token, "/style-preferences", "PUT", prefs);
export const generateRecommendations = (
  token: string,
  count: number,
  body?: StoredProfile,
) =>
  json<{
    items: Recommendation[];
    message: string;
    stats: { evaluated: number };
  }>(token, "/recommendations", "POST", {
    count,
    ...(body ? { body, body_processing_consent: true } : {}),
  });
export const listRecommendations = (
  token: string,
  savedOnly: boolean,
  offset = 0,
) =>
  json<Recommendation[]>(
    token,
    `/recommendations?saved_only=${savedOnly}&limit=30&offset=${offset}`,
  );
export const saveRecommendation = (token: string, id: string) =>
  json<Recommendation>(token, `/recommendations/${id}/save`, "POST");
export const feedbackRecommendation = (
  token: string,
  id: string,
  feedback: Recommendation["feedback"],
) =>
  json<Recommendation>(token, `/recommendations/${id}/feedback`, "POST", {
    feedback,
  });
export const applyRecommendation = (
  token: string,
  id: string,
  mannequin_id?: string,
) =>
  json<AppliedRecommendation>(token, `/recommendations/${id}/apply`, "POST", {
    mannequin_id,
  });
export async function deleteRecommendation(token: string, id: string) {
  await request(`/recommendations/${id}`, token, { method: "DELETE" });
}
