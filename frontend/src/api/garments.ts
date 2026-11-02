import type { Photos, GarmentDraft } from "../types/domain";
import type {
  Analysis,
  Auth,
  Classification,
  GarmentInfo,
  OcrResult,
  StoredGarment,
} from "../features/garments/types";

const base = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

async function request(path: string, token?: string, init: RequestInit = {}) {
  const response = await fetch(`${base}${path}`, {
    ...init,
    cache: "no-store",
    signal: init.signal || AbortSignal.timeout(120000),
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(
      data?.error?.message ||
        `요청 실패 (${response.status}). 다시 시도해 주세요.`,
    );
  }
  return response;
}
export async function authenticate(
  mode: "login" | "register",
  username: string,
  password: string,
): Promise<Auth> {
  return (
    await request(`/auth/${mode}`, undefined, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    })
  ).json();
}
export async function logout(token: string) {
  await request("/auth/logout", token, { method: "POST" });
}
export async function removeAccount(
  token: string,
  username: string,
  password: string,
) {
  await request("/auth/account", token, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}
export async function infer<T>(
  token: string,
  operation: "analyze" | "segment" | "ocr",
  photo: File,
  query = "",
): Promise<T> {
  return (
    await request(`/garments/${operation}${query}`, token, {
      method: "POST",
      body: photo,
      headers: {
        "Content-Type": photo.type,
        "X-Upload-Rights": "confirmed",
        "X-Image-Processing-Consent": "confirmed",
      },
    })
  ).json();
}
export const classify = (token: string, file: File) =>
  infer<Classification>(token, "analyze", file);
export const recognize = (token: string, file: File, kind: string) =>
  infer<OcrResult>(token, "ocr", file, `?kind=${kind}`);
export async function segment(token: string, file: File, x = 0.5, y = 0.5) {
  const result = await infer<{
    png: string;
    model: string;
    predicted_iou: number;
    warnings: string[];
  }>(token, "segment", file, `?x=${x}&y=${y}`);
  const binary = Uint8Array.from(atob(result.png), (c) => c.charCodeAt(0));
  return {
    ...result,
    file: new File([binary], "cutout.png", { type: "image/png" }),
  };
}
async function encode(file: File) {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 32768)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 32768));
  return { content_type: file.type, data: btoa(binary) };
}
export async function saveGarment(
  token: string,
  info: GarmentInfo,
  analysis: Analysis,
  photos: Photos,
  cutouts: Partial<Record<"front" | "back", File>>,
): Promise<StoredGarment> {
  const entries = [
    ...Object.entries(photos),
    ...Object.entries(cutouts).map(
      ([slot, file]) => [`cutout_${slot}`, file] as const,
    ),
  ];
  const images = Object.fromEntries(
    await Promise.all(
      entries
        .filter((entry): entry is [string, File] => !!entry[1])
        .map(async ([slot, file]) => [slot, await encode(file)]),
    ),
  );
  return (
    await request("/garments", token, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Upload-Rights": "confirmed",
        "X-Image-Storage-Consent": "confirmed",
      },
      body: JSON.stringify({ info, analysis, images }),
    })
  ).json();
}
export async function hydrateGarment(
  token: string,
  item: StoredGarment,
): Promise<GarmentDraft> {
  const entries = await Promise.all(
    Object.entries(item.assets).map(async ([slot, asset]) => {
      const blob = await (await request(`/assets/${asset.id}`, token)).blob();
      return [
        slot,
        new File([blob], asset.id, { type: asset.content_type }),
      ] as const;
    }),
  );
  const files = Object.fromEntries(entries);
  if (!files.front) throw new Error("앞면 사진이 없는 의류입니다.");
  return {
    id: item.id,
    ...item.info,
    photos: {
      front: files.front,
      back: files.back,
      size: files.size,
      material: files.material,
    },
    cutouts: { front: files.cutout_front, back: files.cutout_back },
    info: item.info,
    analysis: item.analysis,
    created_at: item.created_at,
    source: "server",
    revision: item.revision,
    user_id: item.user_id,
  };
}
export async function loadWardrobe(token: string) {
  const items: StoredGarment[] = await (
    await request("/garments", token)
  ).json();
  // 동시 사진 디코딩/메모리 피크를 줄인다.
  const garments: GarmentDraft[] = [];
  for (const item of items) garments.push(await hydrateGarment(token, item));
  return garments;
}
export async function updateGarment(
  token: string,
  id: string,
  info: GarmentInfo,
  revision: number,
): Promise<StoredGarment> {
  return (
    await request(`/garments/${id}`, token, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ info, revision }),
    })
  ).json();
}
export async function deleteGarment(token: string, id: string) {
  await request(`/garments/${id}`, token, { method: "DELETE" });
}
export async function reportIssue(
  token: string,
  reason: string,
  garment_id?: string,
): Promise<{ id: string; status: string }> {
  return (
    await request("/reports", token, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason, garment_id }),
    })
  ).json();
}
export async function getReports(
  token: string,
): Promise<{ id: string; status: string }[]> {
  return (await request("/reports", token)).json();
}
