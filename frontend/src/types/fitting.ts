import type { BodyMode, BodyProfile } from "../features/body/types";
import type { GarmentInfo, ModelMetadata } from "../features/garments/types";
import type { Category, Measurements } from "./domain";

export interface FitAdjustment {
  shoulder: number;
  chest: number;
  waist: number;
  hip: number;
  sleeve: number;
  length: number;
  offset_y: number;
  clearance: number;
  hidden: boolean;
}
export const defaultAdjustment: FitAdjustment = {
  shoulder: 1,
  chest: 1,
  waist: 1,
  hip: 1,
  sleeve: 1,
  length: 1,
  offset_y: 0,
  clearance: 0.012,
  hidden: false,
};
export type SlotSelection = Partial<Record<Category, string>>;
export type Adjustments = Record<Category, FitAdjustment>;
export function emptyAdjustments(): Adjustments {
  return {
    top: { ...defaultAdjustment },
    bottom: { ...defaultAdjustment },
    outer: { ...defaultAdjustment, clearance: 0.02 },
  };
}
export interface FittingResource {
  garment_id: string;
  name: string;
  category: Category;
  info: GarmentInfo;
  model_asset_id: string;
  reconstruction_mode: "A" | "B";
  rights_version: number;
  status: "available";
  metadata: ModelMetadata & { fitting_contract?: string };
}
export interface StoredProfile {
  mode: BodyMode;
  values: Record<keyof Measurements, number | null>;
  origins: BodyProfile["origins"];
}
export interface FittingState {
  id: string;
  mannequin_id: string | null;
  mannequin: StoredProfile | null;
  slots: Partial<
    Record<
      Category,
      | FittingResource
      | { garment_id: string; status: "unavailable"; reason: string }
      | null
    >
  >;
  adjustments: Adjustments;
  warnings: string[];
  revision: number | null;
  name: string | null;
  created_at: string;
}
export interface FittingInput {
  mannequin: StoredProfile;
  body_storage_consent: boolean;
  slots: SlotSelection;
  adjustments: Adjustments;
}
export interface StudioDraft {
  recommendation_id?: string;
  owner_id: string | null;
  selected: SlotSelection;
  adjustments: Adjustments;
  pins: Partial<Record<Category, string>>;
  saved?: { id: string; revision: number };
  mannequin_id?: string;
  warnings?: string[];
}
export function newStudioDraft(): StudioDraft {
  return {
    owner_id: null,
    selected: {},
    adjustments: emptyAdjustments(),
    pins: {},
  };
}
