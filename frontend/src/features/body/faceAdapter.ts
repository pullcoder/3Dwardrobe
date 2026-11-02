import type { FaceLandmarker } from "@mediapipe/tasks-vision";
import type { FaceLandmarkProvider } from "./types";

// 검증·라이선스 확인된 Face Landmarker를 전달받는 확장 경계다.
// 현재 앱은 얼굴 가중치를 로드하지 않고 neutralFaceProvider만 제공한다.
export function createFaceLandmarkProvider(
  detector: Pick<FaceLandmarker, "detect">,
): FaceLandmarkProvider {
  return {
    available: true,
    analyze: async (image) => {
      const result = detector.detect(image);
      if (result.faceLandmarks.length !== 1)
        throw new Error("얼굴 한 개의 특징점을 안정적으로 찾지 못했습니다.");
      return result.faceLandmarks[0].map(({ x, y, z }) => ({ x, y, z }));
    },
  };
}
