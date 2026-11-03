import type {
  Analysis,
  GarmentInfo,
  ReconstructionPolicy,
} from "../features/garments/types";

export type Route =
  | "home"
  | "body"
  | "mannequin"
  | "upload"
  | "studio"
  | "recommend"
  | "closet"
  | "settings";
export type Category = "top" | "bottom" | "outer";
export const categories: Record<Category, string> = {
  top: "상의",
  bottom: "하의",
  outer: "겉옷",
};
export type PhotoSlot = "front" | "back" | "size" | "material";
export type Photos = Partial<Record<PhotoSlot, File>>;
export type Measurements = Record<
  "height" | "shoulder" | "chest" | "waist" | "hip" | "arm" | "leg",
  string
>;
export const measurementFields: {
  key: keyof Measurements;
  label: string;
  min: number;
  max: number;
}[] = [
  { key: "height", label: "키", min: 80, max: 250 },
  { key: "shoulder", label: "어깨너비", min: 15, max: 90 },
  { key: "chest", label: "가슴둘레", min: 30, max: 250 },
  { key: "waist", label: "허리둘레", min: 30, max: 250 },
  { key: "hip", label: "엉덩이둘레", min: 30, max: 250 },
  { key: "arm", label: "팔 길이", min: 15, max: 120 },
  { key: "leg", label: "다리 길이", min: 20, max: 150 },
];
export const emptyMeasurements: Measurements = {
  height: "",
  shoulder: "",
  chest: "",
  waist: "",
  hip: "",
  arm: "",
  leg: "",
};
export interface GarmentDraft {
  id: string;
  name: string;
  category: Category;
  color: string;
  material: string;
  size: string;
  photos: Photos;
  reconstruction?: ReconstructionPolicy;
  model_3d_status?: string;
  created_at: string;
  source: "user_entered" | "server";
  user_id?: string;
  revision?: number;
  info?: GarmentInfo;
  analysis?: Analysis;
  cutouts?: Partial<Record<"front" | "back", File>>;
}
export interface UploadValidation {
  content_type: string;
  size_bytes: number;
  width: number;
  height: number;
  retained: false;
  ai_processed: false;
}
