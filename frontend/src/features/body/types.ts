import type { Measurements } from "../../types/domain";

export type BodyMode = "manual" | "photo";
export type MeasurementKey = keyof Measurements;
export type MeasurementOrigin = "estimated" | "user_entered";
export interface Landmark {
  x: number;
  y: number;
  z: number;
  visibility: number;
}
export interface PoseSummary {
  shoulder: number;
  arm: number;
  leg: number;
  torso: number;
  mean_visibility: number;
  method: "projected_2d_v1";
}
export interface BodyProfile {
  values: Measurements;
  origins: Partial<Record<MeasurementKey, MeasurementOrigin>>;
  ratios?: PoseSummary;
  saved_at?: string;
}
export type BodyProfiles = Record<BodyMode, BodyProfile>;
export const defaultBody: Record<MeasurementKey, number> = {
  height: 170,
  shoulder: 40,
  chest: 90,
  waist: 75,
  hip: 94,
  arm: 55,
  leg: 80,
};
export interface PoseAnalysis {
  landmarks: Landmark[];
  summary: PoseSummary;
  width: number;
  height: number;
}

// 실제 Face Landmarker는 아직 도입하지 않는다. 얼굴 원본 텍스처를 받는 인터페이스도 두지 않는다.
export interface FaceLandmarkProvider {
  readonly available: boolean;
  analyze(
    image: ImageBitmap,
  ): Promise<ReadonlyArray<Pick<Landmark, "x" | "y" | "z">>>;
}
export const neutralFaceProvider: FaceLandmarkProvider = {
  available: false,
  analyze: async () => {
    throw new Error(
      "얼굴 특징점 분석은 연결 전입니다. 중립 얼굴을 사용합니다.",
    );
  },
};
