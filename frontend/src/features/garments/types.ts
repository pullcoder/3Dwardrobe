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
export interface ReconstructionPolicy {
  reconstruction_mode: "A" | "B";
  source_type: "self_photographed" | "licensed_image" | "other";
  rights_status: "unverified" | "pending" | "approved" | "rejected";
  license_reference: string | null;
  original_image_retention: "temporary" | "consented_storage";
  generated_model_path: string | null;
  model_visibility: "private";
  rights_reviewed_at: string | null;
}
export const defaultPolicy: ReconstructionPolicy = {
  reconstruction_mode: "A",
  source_type: "other",
  rights_status: "unverified",
  license_reference: null,
  original_image_retention: "temporary",
  generated_model_path: null,
  model_visibility: "private",
  rights_reviewed_at: null,
};
export const rightsLabels: Record<
  ReconstructionPolicy["rights_status"],
  string
> = {
  unverified: "미확인",
  pending: "검토 중",
  approved: "승인",
  rejected: "거절",
};
export interface StoredGarment extends ReconstructionPolicy {
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

export type RightStatus =
  "unverified" | "confirmed" | "pending" | "verified" | "rejected" | "disputed";
export interface ModelMetadata {
  category: Category;
  garment_type: string;
  unit: "meter";
  coordinate_system: "y_up_z_front";
  bounds: { min: [number, number, number]; max: [number, number, number] };
  dimensions: Record<string, { value: number; source: string }>;
  mode: "A" | "B";
  version: string;
  created_at: string;
  back_geometry: "estimated";
  warnings: string[];
  triangle_count: number;
  mesh_names: string[];
  physical_simulation: false;
}
export interface GenerationState {
  garment_id: string;
  selected_mode: "A" | "B" | null;
  b_available: boolean;
  photo_rights_status: RightStatus;
  detailed_rights_status: RightStatus;
  output_rights_status: RightStatus;
  rights_version: number;
  rights_reviewed_at: string | null;
  generation_status:
    "idle" | "queued" | "processing" | "completed" | "failed" | "cancelled";
  job_id: string | null;
  stage: string;
  generation_error: string | null;
  model_ready: boolean;
  model_format: "glb" | null;
  model_version: string | null;
  model_metadata: ModelMetadata | null;
  supported_types: string[];
}
