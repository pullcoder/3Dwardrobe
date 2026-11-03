import type { GarmentInfo } from "../garments/types";
import type { Category } from "../../types/domain";
import type { SlotSelection, StoredProfile } from "../../types/fitting";

export interface Preferences {
  styles: string[];
  fit: string;
  preferred_colors: string[];
  avoided_colors: string[];
  preferred_types: string[];
  purpose: string;
  season: string;
  mood: string;
  revision: number;
}
export interface Recommendation {
  id: string;
  name: string;
  reasons: string[];
  notes: string[];
  engine: string;
  body_used: boolean;
  items: {
    id: string;
    part: Category;
    name: string;
    info: GarmentInfo;
    model_ready: boolean;
    reconstruction_mode: "A" | "B";
  }[];
  slots: SlotSelection;
  available: boolean;
  fitting_available: boolean;
  warnings: string[];
  feedback: "none" | "like" | "dislike" | "exclude";
  saved_at: string | null;
  created_at: string;
  mannequin_id: string | null;
}
export interface AppliedRecommendation {
  recommendation_id: string;
  slots: SlotSelection;
  pins: Partial<Record<Category, string>>;
  mannequin_id: string | null;
  mannequin: StoredProfile | null;
}
