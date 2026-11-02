import type { UploadValidation } from "../types/domain";

const baseUrl = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

export async function validateUpload(file: File): Promise<UploadValidation> {
  const response = await fetch(`${baseUrl}/uploads/validate`, {
    method: "POST",
    headers: { "Content-Type": file.type, "X-Upload-Rights": "confirmed" },
    body: file,
    signal: AbortSignal.timeout(15000),
    cache: "no-store",
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error?.message || "사진 검증에 실패했습니다.");
  return data as UploadValidation;
}

export async function getHealth(): Promise<{
  features: { ai: boolean; storage: boolean };
  mode: string;
}> {
  const response = await fetch(`${baseUrl}/health`, {
    signal: AbortSignal.timeout(5000),
    cache: "no-store",
  });
  if (!response.ok) throw new Error("로컬 API에 연결할 수 없습니다.");
  return response.json();
}
