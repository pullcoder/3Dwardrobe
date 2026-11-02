// 모듈 Worker의 importScripts 제약을 피하기 위해 공식 CJS 번들을 격리해 로드한다.
globalThis.exports = {};
importScripts('/mediapipe/vision_bundle.js');
const { FilesetResolver, PoseLandmarker } = globalThis.exports;
let landmarker;
globalThis.onmessage = async (event) => {
  const { bitmap } = event.data;
  try {
    if (!landmarker) {
      globalThis.postMessage({ type: 'progress', message: 'MediaPipe 모델을 준비하고 있어요.' });
      const files = await FilesetResolver.forVisionTasks('/mediapipe/wasm');
      landmarker = await PoseLandmarker.createFromOptions(files, {
        canvas: new OffscreenCanvas(1, 1),
        baseOptions: { modelAssetPath: '/mediapipe/pose_landmarker_full.task', delegate: 'CPU' },
        runningMode: 'IMAGE', numPoses: 2,
        minPoseDetectionConfidence: 0.5, minPosePresenceConfidence: 0.5,
        outputSegmentationMasks: false,
      });
    }
    globalThis.postMessage({ type: 'progress', message: '사진 안에서 신체 관절을 찾고 있어요.' });
    const result = landmarker.detect(bitmap);
    globalThis.postMessage({ type: 'result', landmarks: result.landmarks });
  } catch {
    // SDK 예외에 사용자 이미지 정보가 포함될 수 있어 원문을 전달하지 않는다.
    globalThis.postMessage({ type: 'error', message: '분석 엔진을 실행하지 못했습니다. 모델 파일과 브라우저 WebGL 지원을 확인하고 다시 시도해 주세요.' });
  } finally { bitmap.close(); }
};
