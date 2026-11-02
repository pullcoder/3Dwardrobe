import type { Category } from "../../types/domain";

export interface Measurement {
  label: string;
  size: string | null;
  value: number | null;
  unit: "cm" | "mm" | "inch" | "unknown";
  kind: "flat" | "circumference" | "length" | "unknown";
  target: "garment" | "body" | "unknown";
  source: "ocr" | "user_entered";
}
export interface Composition {
  name: string;
  percent: number | null;
  source: "ocr" | "user_entered";
}
export interface GarmentInfo {
  name: string;
  category: Category;
  garment_type: string;
  color: string;
  secondary_color: string | null;
  pattern: string;
  sleeve: string;
  neckline: string;
  fit: string;
  visual_features: string;
  size: string;
  material: string;
  composition: Composition[];
  measurements: Measurement[];
  description: string;
}
export const blankInfo: GarmentInfo = {
  name: "",
  category: "top",
  garment_type: "unknown",
  color: "",
  secondary_color: null,
  pattern: "unknown",
  sleeve: "unknown",
  neckline: "unknown",
  fit: "unknown",
  visual_features: "",
  size: "",
  material: "미확인",
  composition: [],
  measurements: [],
  description: "",
};
export const garmentTypes = [
  "티셔츠",
  "셔츠",
  "니트",
  "후드티",
  "맨투맨",
  "카디건",
  "재킷",
  "코트",
  "패딩",
  "청바지",
  "슬랙스",
  "반바지",
  "스커트",
  "기타",
  "unknown",
];
export interface Classification {
  model: string;
  garment_type: string;
  category: Category | null;
  primary_color: string;
  secondary_color: string | null;
  pattern: string;
  sleeve: string;
  neckline: string;
  fit: string;
  visual_features: string | null;
  material: string | null;
  scores: Record<
    string,
    { value: string; candidate: string; similarity: number; margin: number }
  >;
  warnings: string[];
}
export interface OcrResult {
  model: string;
  text: string;
  confidence: number;
  sizes: string[];
  measurements: Measurement[];
  composition: Composition[];
  warnings: string[];
}
export interface Analysis {
  processing_status?: "completed" | "partial";
  errors?: string[];
  front?: Classification;
  back?: Classification;
  size?: OcrResult;
  material?: OcrResult;
  segmentation?: Partial<
    Record<"front" | "back", { model: string; predicted_iou: number }>
  >;
}
export interface StoredGarment {
  id: string;
  user_id: string;
  info: GarmentInfo;
  analysis: Analysis;
  created_at: string;
  revision: number;
  analysis_status: string;
  model_3d_status: string;
  assets: Record<string, { id: string; content_type: string }>;
}
export interface Auth {
  token: string;
  user: { id: string; username: string };
}
